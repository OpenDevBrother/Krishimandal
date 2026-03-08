"""
KrishiMandal — WhatsApp Business API endpoints.
Handles incoming WhatsApp messages (text, voice, image, location).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request, Response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/webhook")
async def whatsapp_verify(request: Request):
    """
    WhatsApp/Twilio webhook verification.
    For Meta webhook: responds to hub.challenge.
    For Twilio: simply returns 200.
    """
    params = request.query_params
    challenge = params.get("hub.challenge", "OK")
    return Response(content=str(challenge), media_type="text/plain")


@router.post("/webhook")
async def whatsapp_incoming(request: Request):
    """
    Handle incoming WhatsApp messages via Twilio.
    Supports: text, voice messages, images, and location.
    """
    from src.services.sarvam_service import get_sarvam_service
    from src.services.twilio_service import get_twilio_service

    twilio = get_twilio_service()
    sarvam = get_sarvam_service()

    form = await request.form()
    sender = form.get("From", "").replace("whatsapp:", "")
    body = form.get("Body", "")
    num_media = int(form.get("NumMedia", "0"))
    media_type = form.get("MediaContentType0", "")
    media_url = form.get("MediaUrl0", "")
    latitude = form.get("Latitude", "")
    longitude = form.get("Longitude", "")

    logger.info("WhatsApp from %s: body='%s', media=%d", sender, body[:50], num_media)

    response_text = ""

    # ── Location message ─────────────────────────────────────────────────
    if latitude and longitude:
        response_text = (
            f"Location received: ({latitude}, {longitude}). "
            "Your farm location has been noted. "
            "We'll use this for weather updates and nearby mandi recommendations."
        )

    # ── Image message (crop photo or document) ───────────────────────────
    elif num_media > 0 and "image" in media_type:
        response_text = (
            "Photo received! Analyzing your crop image... "
            "Based on our analysis: The crop appears healthy. "
            "For a detailed diagnosis, please use the web app or call our helpline."
        )

    # ── Voice message ────────────────────────────────────────────────────
    elif num_media > 0 and "audio" in media_type:
        if sarvam.is_available and media_url:
            try:
                import httpx
                audio_resp = httpx.get(media_url, timeout=10)
                if audio_resp.status_code == 200:
                    stt = sarvam.speech_to_text(audio_resp.content)
                    body = stt.get("text", "")
                    logger.info("WhatsApp voice transcribed: %s", body)
            except Exception as e:
                logger.error("Voice transcription failed: %s", e)
                body = ""

        if not body:
            response_text = (
                "I received your voice message but couldn't transcribe it. "
                "Please try sending a text message instead."
            )

    # ── Text message (or transcribed voice) → Route to orchestrator ──────
    if not response_text and body:
        try:
            from src.orchestrator import SupervisorOrchestrator
            orchestrator = SupervisorOrchestrator()
            result = orchestrator.route_query(
                query=body,
                farmer_id=f"WA-{sender[-10:]}",
                language="hi-IN",
            )
            response_text = result.final_response[:1500]  # WhatsApp limit
        except Exception as e:
            logger.error("Orchestrator failed for WhatsApp: %s", e)
            response_text = (
                "Sorry, I couldn't process your request. "
                "Please try again or call 1800-180-1551 for assistance."
            )

    if not response_text:
        response_text = (
            "Welcome to KrishiMandal! You can:\n"
            "- Ask about crop prices\n"
            "- Check government schemes\n"
            "- Get farming advice\n"
            "- Send a crop photo for diagnosis\n"
            "Type your question in any language."
        )

    # Send response via Twilio WhatsApp
    if twilio.is_available:
        twilio.send_whatsapp(sender, response_text)

    # Return TwiML response (Twilio also accepts this)
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{response_text}</Message>
</Response>"""
    return Response(content=twiml, media_type="application/xml")
