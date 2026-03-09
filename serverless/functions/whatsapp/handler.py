"""
KrishiMandal Serverless — WhatsApp Lambda
Handles:
  1. POST /whatsapp/send — Send a WhatsApp message to a farmer
  2. POST /whatsapp/digest — Send daily digest (triggered by scheduled rule)
  3. EventBridge events — Real-time alerts via WhatsApp
"""
import json
import logging
from datetime import datetime, timezone

from common.dynamo_repository import get_repository
from common.twilio_whatsapp import send_whatsapp, is_configured
from common.events import event_to_notification
from common.response import ok, bad_request, error

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _get_farmer_phone(farmer_id: str) -> str | None:
    """Get farmer's phone number from DynamoDB profile."""
    repo = get_repository()
    farm = repo.get_farm(farmer_id)
    if not farm:
        return None
    phone = farm.get("phone", "")
    if not phone:
        return None
    # Ensure +91 prefix for Indian numbers
    phone = phone.strip()
    if not phone.startswith("+"):
        if phone.startswith("91") and len(phone) >= 12:
            phone = f"+{phone}"
        else:
            phone = f"+91{phone}"
    return phone


def _is_whatsapp_enabled(farmer_id: str) -> bool:
    """Check if farmer has opted in to WhatsApp notifications."""
    repo = get_repository()
    farm = repo.get_farm(farmer_id)
    if not farm:
        return False
    return farm.get("whatsapp_enabled", False)


def _send_to_farmer(farmer_id: str, message: str) -> dict:
    """Send WhatsApp message to a farmer by ID."""
    if not is_configured():
        return {"success": False, "error": "Twilio not configured"}

    if not _is_whatsapp_enabled(farmer_id):
        return {"success": False, "error": "WhatsApp not enabled for this farmer"}

    phone = _get_farmer_phone(farmer_id)
    if not phone:
        return {"success": False, "error": "No phone number found"}

    return send_whatsapp(phone, message)


def _build_digest(farmer_id: str) -> str:
    """Build a daily digest message for a farmer."""
    repo = get_repository()
    lines = ["🌾 *KrishiMandal Daily Digest*", ""]

    # Unread notifications
    notifs = repo.get_notifications(farmer_id)
    unread = [n for n in notifs if not n.get("is_read", False)]
    if unread:
        lines.append(f"📬 *{len(unread)} Unread Alerts:*")
        for n in unread[:5]:
            lines.append(f"  • {n.get('title', 'Alert')}")
        if len(unread) > 5:
            lines.append(f"  ... and {len(unread) - 5} more")
        lines.append("")

    # Low stock items
    low_stock = repo.get_low_stock_items(farmer_id)
    if low_stock:
        lines.append(f"⚠️ *{len(low_stock)} Low Stock Items:*")
        for item in low_stock[:5]:
            name = item.get("name", "Item")
            qty = item.get("quantity", 0)
            unit = item.get("unit", "")
            lines.append(f"  • {name}: {qty} {unit}")
        lines.append("")

    # Farm quick status (if state exists)
    farm = repo.get_farm(farmer_id)
    if farm:
        lines.append(f"🧑‍🌾 *Farm:* {farm.get('farmer_name', farmer_id)}")
        crop = farm.get("current_crop", "")
        if crop:
            lines.append(f"🌱 *Crop:* {crop}")

    if len(lines) <= 2:
        lines.append("✅ All clear! No new alerts today.")

    lines.append("")
    lines.append(f"📅 {datetime.now(timezone.utc).strftime('%d %b %Y')}")
    lines.append("_Open KrishiMandal app for details_")

    return "\n".join(lines)


def handler(event, context):
    """Lambda handler for WhatsApp operations."""

    # ── EventBridge trigger (real-time alerts) ──
    if "detail-type" in event or "source" in event:
        return _handle_eventbridge(event)

    # ── Scheduled trigger (daily digest) ──
    if event.get("source") == "aws.events" or "Digest" in str(event.get("resources", [])):
        return _handle_digest()

    # ── API Gateway trigger ──
    try:
        path = event.get("path", "")
        method = event.get("httpMethod", "POST")

        if method == "OPTIONS":
            return ok({})

        body = json.loads(event.get("body", "{}") or "{}")

        # POST /whatsapp/send — Direct message send
        if path.endswith("/whatsapp/send"):
            farmer_id = body.get("farmer_id", "")
            message = body.get("message", "")
            if not farmer_id:
                return bad_request("farmer_id is required")
            if not message:
                return bad_request("message is required")

            result = _send_to_farmer(farmer_id, message)
            return ok(result)

        # POST /whatsapp/opt-in — Enable WhatsApp for farmer
        if path.endswith("/whatsapp/opt-in"):
            farmer_id = body.get("farmer_id", "")
            enabled = body.get("enabled", True)
            if not farmer_id:
                return bad_request("farmer_id is required")

            repo = get_repository()
            repo.update_farm(farmer_id, {"whatsapp_enabled": enabled})
            return ok({
                "farmer_id": farmer_id,
                "whatsapp_enabled": enabled,
                "message": "WhatsApp notifications " + ("enabled" if enabled else "disabled"),
            })

        # POST /whatsapp/digest — Manual digest trigger
        if path.endswith("/whatsapp/digest"):
            farmer_id = body.get("farmer_id")
            if farmer_id:
                digest = _build_digest(farmer_id)
                result = _send_to_farmer(farmer_id, digest)
                return ok({"farmer_id": farmer_id, **result})
            else:
                return _handle_digest()

        return bad_request(f"Unknown whatsapp path: {path}")

    except Exception as e:
        logger.error("WhatsApp handler failed: %s", e, exc_info=True)
        return error(str(e))


def _handle_eventbridge(event):
    """Handle EventBridge events — send real-time WhatsApp alerts."""
    try:
        event_type = event.get("detail-type", "")
        detail = event.get("detail", {})
        farmer_id = detail.get("farmer_id", "")

        if not farmer_id:
            logger.warning("EventBridge event missing farmer_id: %s", event_type)
            return

        # Check if farmer has WhatsApp enabled
        if not _is_whatsapp_enabled(farmer_id):
            logger.info("WhatsApp not enabled for %s, skipping", farmer_id)
            return

        # Build alert message
        notif = event_to_notification(event_type, detail)
        emoji_map = {
            "INVENTORY_LOW_STOCK": "📦",
            "HEALTH_DECLINED": "🌿",
            "PEST_DETECTED": "🐛",
            "PRICE_ALERT": "💰",
            "HARVEST_PREDICTED": "🌾",
            "SCHEME_DEADLINE": "📋",
            "APPLICATION_STATUS_CHANGED": "📄",
        }
        emoji = emoji_map.get(event_type, "🔔")

        message = (
            f"{emoji} *KrishiMandal Alert*\n\n"
            f"*{notif['title']}*\n"
            f"{notif['message']}\n\n"
            f"_Open the app for details_"
        )

        result = _send_to_farmer(farmer_id, message)
        logger.info("WhatsApp alert for %s (%s): %s", farmer_id, event_type, result)

    except Exception as e:
        logger.error("EventBridge WhatsApp handler failed: %s", e, exc_info=True)


def _handle_digest():
    """Send daily digest to all farmers with WhatsApp enabled."""
    try:
        repo = get_repository()
        # Scan for all farm profiles with whatsapp_enabled=True
        # In production, use a GSI. For now, scan FARM profiles.
        from boto3.dynamodb.conditions import Attr
        resp = repo._table.scan(
            FilterExpression=Attr("entity_type").eq("FARM_PROFILE") & Attr("whatsapp_enabled").eq(True),
            ProjectionExpression="farmer_id, phone",
        )
        farmers = resp.get("Items", [])

        sent_count = 0
        for farm in farmers:
            fid = farm.get("farmer_id", "")
            if not fid:
                continue
            digest = _build_digest(fid)
            result = _send_to_farmer(fid, digest)
            if result.get("success"):
                sent_count += 1

        logger.info("Daily digest sent to %d farmers", sent_count)
        return ok({"message": f"Digest sent to {sent_count} farmers"})

    except Exception as e:
        logger.error("Digest handler failed: %s", e, exc_info=True)
        return error(str(e))
