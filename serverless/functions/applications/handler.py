"""
KrishiMandal Serverless — Applications Lambda
Scheme application CRUD operations.
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
    """Lambda handler for /farm/{farmer_id}/applications endpoints."""
    try:
        method = event.get("httpMethod", "GET")
        path = event.get("path", "")
        path_params = event.get("pathParameters") or {}
        farmer_id = path_params.get("farmer_id", "")
        repo = get_repository()

        if not farmer_id:
            return bad_request("farmer_id is required.")

        # Extract app_id from path if present: /farm/{fid}/applications/{app_id}
        parts = path.strip("/").split("/")
        app_id = None
        if len(parts) >= 4 and parts[2] == "applications":
            app_id = parts[3] if len(parts) > 3 else None

        # POST /farm/{farmer_id}/applications — create application
        if method == "POST" and not app_id:
            body = json.loads(event.get("body", "{}"))
            scheme_id = body.get("scheme_id")
            if not scheme_id:
                return bad_request("scheme_id is required.")

            status = "submitted" if body.get("submit_directly", False) else "draft"
            data = {
                "scheme_id": scheme_id,
                "status": status,
                "farmer_notes": body.get("farmer_notes", ""),
                "documents_checklist": body.get("documents_checklist", []),
            }
            item = repo.create_application(farmer_id, data)

            if status == "submitted":
                publish_event("APPLICATION_SUBMITTED", {
                    "scheme_id": scheme_id,
                    "application_id": item["id"],
                }, farmer_id=farmer_id)

            clean = {k: v for k, v in item.items() if k not in ("PK", "SK", "GSI1PK", "GSI1SK", "entity_type")}
            return created(clean)

        # GET /farm/{farmer_id}/applications — list applications
        if method == "GET" and not app_id:
            apps = repo.get_applications(farmer_id)
            result = []
            for a in apps:
                clean = {k: v for k, v in a.items() if k not in ("PK", "SK", "GSI1PK", "GSI1SK", "entity_type")}
                result.append(clean)
            return ok(result)

        # Operations on specific application
        if app_id:
            # Find the application
            apps = repo.get_applications(farmer_id)
            app = next((a for a in apps if a.get("id") == app_id), None)
            if not app:
                return not_found("Application not found.")

            # GET /farm/{farmer_id}/applications/{app_id}
            if method == "GET":
                clean = {k: v for k, v in app.items() if k not in ("PK", "SK", "GSI1PK", "GSI1SK", "entity_type")}
                return ok(clean)

            # PUT /farm/{farmer_id}/applications/{app_id}
            if method == "PUT":
                body = json.loads(event.get("body", "{}"))
                action = body.get("action")

                if action == "submit" and app.get("status") == "draft":
                    # Update status in DynamoDB
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc).isoformat()
                    repo._table.update_item(
                        Key={"PK": f"FARM#{farmer_id}", "SK": f"APP#{app_id}"},
                        UpdateExpression="SET #s = :s, submitted_at = :t, GSI1SK = :gsi",
                        ExpressionAttributeNames={"#s": "status"},
                        ExpressionAttributeValues={
                            ":s": "submitted",
                            ":t": now,
                            ":gsi": f"submitted#{now}",
                        },
                    )
                    publish_event("APPLICATION_SUBMITTED", {
                        "scheme_id": app.get("scheme_id"),
                        "application_id": app_id,
                    }, farmer_id=farmer_id)

                if body.get("farmer_notes") is not None:
                    repo._table.update_item(
                        Key={"PK": f"FARM#{farmer_id}", "SK": f"APP#{app_id}"},
                        UpdateExpression="SET farmer_notes = :n",
                        ExpressionAttributeValues={":n": body["farmer_notes"]},
                    )

                return ok({"message": "Application updated.", "application_id": app_id})

            # DELETE /farm/{farmer_id}/applications/{app_id} — withdraw
            if method == "DELETE":
                if app.get("status") in ("approved", "rejected"):
                    return bad_request(f"Cannot withdraw application with status '{app.get('status')}'.")

                repo._table.update_item(
                    Key={"PK": f"FARM#{farmer_id}", "SK": f"APP#{app_id}"},
                    UpdateExpression="SET #s = :s",
                    ExpressionAttributeNames={"#s": "status"},
                    ExpressionAttributeValues={":s": "withdrawn"},
                )

                publish_event("APPLICATION_STATUS_CHANGED", {
                    "application_id": app_id,
                    "status": "withdrawn",
                }, farmer_id=farmer_id)

                return ok({"message": "Application withdrawn.", "application_id": app_id})

        return bad_request("Unsupported operation.")

    except Exception as e:
        logger.error("Applications handler failed: %s", e, exc_info=True)
        fb = fallback_to_ec2(
            method=event.get("httpMethod", "GET"),
            path=event.get("path", ""),
            body=json.loads(event.get("body", "{}")) if event.get("body") else None,
        )
        return fb or error(str(e))
