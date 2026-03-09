"""
KrishiMandal Serverless — Inventory Lambda
Inventory management CRUD, alerts, stock adjustments.
"""
import json
import logging

from common.dynamo_repository import get_repository
from common.events import publish_event
from common.fallback import fallback_to_ec2
from common.response import ok, created, bad_request, not_found, error

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event, context):
    """Lambda handler for /farm/{farmer_id}/inventory endpoints."""
    try:
        method = event.get("httpMethod", "GET")
        path = event.get("path", "")
        path_params = event.get("pathParameters") or {}
        farmer_id = path_params.get("farmer_id", "")
        repo = get_repository()

        if not farmer_id:
            return bad_request("farmer_id is required.")

        # Parse item_id and sub-action from path
        parts = path.strip("/").split("/")
        item_id = None
        sub_action = None
        # /farm/{fid}/inventory/{item_id}/adjust
        if len(parts) >= 4 and parts[2] == "inventory":
            if parts[3] == "alerts":
                sub_action = "alerts"
            elif len(parts) > 3:
                item_id = parts[3]
                if len(parts) > 4:
                    sub_action = parts[4]  # "adjust"

        # GET /farm/{farmer_id}/inventory/alerts
        if method == "GET" and sub_action == "alerts":
            items = repo.get_low_stock_items(farmer_id)
            result = [_clean(i) for i in items]
            return ok(result)

        # POST /farm/{farmer_id}/inventory — add item
        if method == "POST" and not item_id:
            body = json.loads(event.get("body", "{}"))
            if not body.get("name"):
                return bad_request("Item name is required.")

            data = {
                "name": body.get("name", ""),
                "category": body.get("category", "general"),
                "quantity": body.get("quantity", 0),
                "unit": body.get("unit", "kg"),
                "alert_threshold": body.get("alert_threshold", 0),
                "purchase_price": body.get("purchase_price", 0),
                "purchase_date": body.get("purchase_date", ""),
                "expiry_date": body.get("expiry_date", ""),
                "notes": body.get("notes", ""),
            }
            item = repo.create_inventory_item(farmer_id, data)
            return created(_clean(item))

        # GET /farm/{farmer_id}/inventory — list items
        if method == "GET" and not item_id:
            items = repo.get_inventory(farmer_id)
            qs = event.get("queryStringParameters") or {}
            category = qs.get("category")
            if category:
                items = [i for i in items if i.get("category") == category]
            return ok([_clean(i) for i in items])

        # Operations on specific item
        if item_id:
            # POST /farm/{fid}/inventory/{item_id}/adjust
            if method == "POST" and sub_action == "adjust":
                body = json.loads(event.get("body", "{}"))
                adjustment = body.get("adjustment", 0)
                if not adjustment:
                    return bad_request("adjustment value is required.")

                item = repo.get_inventory_item(farmer_id, item_id)
                if not item:
                    return not_found("Inventory item not found.")

                new_qty = max(0, item.get("quantity", 0) + adjustment)
                updated = repo.update_inventory_item(farmer_id, item_id, {"quantity": new_qty})

                # Check low stock
                threshold = item.get("alert_threshold", 0)
                if threshold > 0 and new_qty <= threshold:
                    publish_event("INVENTORY_LOW_STOCK", {
                        "item_id": item_id,
                        "item_name": item.get("name", ""),
                        "quantity": new_qty,
                        "unit": item.get("unit", ""),
                    }, farmer_id=farmer_id)

                return ok(_clean(updated))

            # GET /farm/{fid}/inventory/{item_id}
            if method == "GET":
                item = repo.get_inventory_item(farmer_id, item_id)
                if not item:
                    return not_found("Inventory item not found.")
                return ok(_clean(item))

            # PUT /farm/{fid}/inventory/{item_id}
            if method == "PUT":
                body = json.loads(event.get("body", "{}"))
                updates = {k: v for k, v in body.items() if v is not None and k not in ("farmer_id", "id")}
                if not updates:
                    return bad_request("No updates provided.")

                item = repo.get_inventory_item(farmer_id, item_id)
                if not item:
                    return not_found("Inventory item not found.")

                updated = repo.update_inventory_item(farmer_id, item_id, updates)
                return ok(_clean(updated))

            # DELETE /farm/{fid}/inventory/{item_id}
            if method == "DELETE":
                item = repo.get_inventory_item(farmer_id, item_id)
                if not item:
                    return not_found("Inventory item not found.")
                repo.delete_inventory_item(farmer_id, item_id)
                return ok({"message": "Inventory item deleted.", "item_id": item_id})

        return bad_request("Unsupported operation.")

    except Exception as e:
        logger.error("Inventory handler failed: %s", e, exc_info=True)
        fb = fallback_to_ec2(
            method=event.get("httpMethod", "GET"),
            path=event.get("path", ""),
            body=json.loads(event.get("body", "{}")) if event.get("body") else None,
        )
        return fb or error(str(e))


def _clean(item: dict) -> dict:
    """Remove DynamoDB internal keys from response."""
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entity_type")}
