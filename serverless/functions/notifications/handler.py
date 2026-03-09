"""
KrishiMandal Serverless — Notifications Lambda
Notification CRUD, unread count, mark read.
Also handles EventBridge notification events.
"""
import json
import logging

from common.dynamo_repository import get_repository
from common.events import event_to_notification
from common.fallback import fallback_to_ec2
from common.response import ok, created, bad_request, not_found, error

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event, context):
    """Lambda handler for notifications — API Gateway + EventBridge triggers."""

    # ── EventBridge trigger (create notification from event) ──
    if "detail-type" in event or "source" in event:
        return _handle_eventbridge(event)

    # ── API Gateway trigger ──
    try:
        method = event.get("httpMethod", "GET")
        path = event.get("path", "")
        path_params = event.get("pathParameters") or {}
        farmer_id = path_params.get("farmer_id", "")
        repo = get_repository()

        if not farmer_id:
            return bad_request("farmer_id is required.")

        parts = path.strip("/").split("/")
        notif_id = None
        sub_action = None
        # /farm/{fid}/notifications/unread-count
        # /farm/{fid}/notifications/read-all
        # /farm/{fid}/notifications/{notif_id}/read
        if len(parts) >= 4 and parts[2] == "notifications":
            token = parts[3]
            if token == "unread-count":
                sub_action = "unread-count"
            elif token == "read-all":
                sub_action = "read-all"
            else:
                notif_id = token
                if len(parts) > 4 and parts[4] == "read":
                    sub_action = "read"

        # GET /farm/{fid}/notifications/unread-count
        if method == "GET" and sub_action == "unread-count":
            count = repo.get_unread_count(farmer_id)
            return ok({"farmer_id": farmer_id, "unread_count": count})

        # PUT /farm/{fid}/notifications/read-all
        if method == "PUT" and sub_action == "read-all":
            repo.mark_all_notifications_read(farmer_id)
            return ok({"farmer_id": farmer_id, "message": "All notifications marked read."})

        # GET /farm/{fid}/notifications — list notifications
        if method == "GET" and not notif_id:
            notifs = repo.get_notifications(farmer_id)
            qs = event.get("queryStringParameters") or {}
            ntype = qs.get("type")
            is_read = qs.get("is_read")
            if ntype:
                notifs = [n for n in notifs if n.get("type") == ntype]
            if is_read is not None:
                read_val = is_read.lower() == "true"
                notifs = [n for n in notifs if n.get("is_read") == read_val]
            return ok([_clean(n) for n in notifs])

        # Operations on specific notification
        if notif_id:
            # PUT /farm/{fid}/notifications/{notif_id}/read
            if method == "PUT" and sub_action == "read":
                repo.mark_notification_read(farmer_id, notif_id)
                return ok({"message": "Notification marked read.", "notif_id": notif_id})

            # GET /farm/{fid}/notifications/{notif_id}
            if method == "GET":
                notifs = repo.get_notifications(farmer_id)
                notif = next((n for n in notifs if n.get("id") == notif_id), None)
                if not notif:
                    return not_found("Notification not found.")
                return ok(_clean(notif))

            # DELETE /farm/{fid}/notifications/{notif_id}
            if method == "DELETE":
                repo._table.delete_item(
                    Key={"PK": f"FARM#{farmer_id}", "SK": f"NOTIF#{notif_id}"}
                )
                return ok({"message": "Notification deleted.", "notif_id": notif_id})

        return bad_request("Unsupported operation.")

    except Exception as e:
        logger.error("Notifications handler failed: %s", e, exc_info=True)
        fb = fallback_to_ec2(
            method=event.get("httpMethod", "GET"),
            path=event.get("path", ""),
        )
        return fb or error(str(e))


def _handle_eventbridge(event):
    """Handle EventBridge events — create notifications from system events."""
    try:
        event_type = event.get("detail-type", "")
        detail = event.get("detail", {})
        farmer_id = detail.get("farmer_id", "")

        if not farmer_id:
            logger.warning("EventBridge event missing farmer_id: %s", event_type)
            return

        notif_data = event_to_notification(event_type, detail)
        repo = get_repository()
        repo.create_notification(farmer_id, notif_data)
        logger.info("Created notification for %s: %s", farmer_id, event_type)

    except Exception as e:
        logger.error("EventBridge notification handler failed: %s", e, exc_info=True)


def _clean(item: dict) -> dict:
    """Remove DynamoDB internal keys from response."""
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entity_type")}
