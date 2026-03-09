"""
KrishiMandal Serverless — Twilio WhatsApp Service
Sends WhatsApp messages via Twilio REST API (sandbox or production).
"""
import base64
import json
import logging
import os
from urllib import request as urllib_request, parse as urllib_parse

logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_NUMBER", "")


def is_configured() -> bool:
    return bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM)


def send_whatsapp(to_phone: str, message: str) -> dict:
    """
    Send a WhatsApp message via Twilio.
    to_phone: Phone number WITH country code, e.g. "+919876543210"
    message: Text message to send (max ~1600 chars for WhatsApp)
    Returns: {"success": True/False, "sid": "...", "error": "..."}
    """
    if not is_configured():
        logger.warning("Twilio not configured — skipping WhatsApp send")
        return {"success": False, "error": "Twilio not configured"}

    # Ensure proper WhatsApp format
    from_num = TWILIO_WHATSAPP_FROM
    if not from_num.startswith("whatsapp:"):
        from_num = f"whatsapp:{from_num}"
    to_num = to_phone
    if not to_num.startswith("whatsapp:"):
        to_num = f"whatsapp:{to_num}"

    url = (
        f"https://api.twilio.com/2010-04-01/Accounts/"
        f"{TWILIO_ACCOUNT_SID}/Messages.json"
    )

    # Truncate message for WhatsApp limit
    if len(message) > 1600:
        message = message[:1597] + "..."

    body = urllib_parse.urlencode({
        "From": from_num,
        "To": to_num,
        "Body": message,
    }).encode("utf-8")

    # Basic auth
    credentials = base64.b64encode(
        f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}".encode()
    ).decode()

    req = urllib_request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            logger.info("WhatsApp sent to %s, SID=%s", to_phone, result.get("sid"))
            return {"success": True, "sid": result.get("sid", "")}
    except Exception as e:
        error_msg = str(e)
        # Try to parse Twilio error response
        if hasattr(e, "read"):
            try:
                err_body = json.loads(e.read().decode())
                error_msg = err_body.get("message", error_msg)
            except Exception:
                pass
        logger.error("WhatsApp send failed to %s: %s", to_phone, error_msg)
        return {"success": False, "error": error_msg}
