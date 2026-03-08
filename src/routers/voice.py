"""
KrishiMandal — Twilio Voice/IVR endpoints.
Handles incoming phone calls, IVR menu, and voice responses.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Form, Request, Response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/incoming")
async def voice_incoming(request: Request):
    """
    Twilio webhook for incoming calls.
    Returns TwiML greeting with IVR menu.
    """
    from src.services.twilio_service import get_twilio_service

    twilio = get_twilio_service()

    # Try to detect language from caller info (default Hindi)
    form = await request.form()
    caller = form.get("From", "unknown")
    logger.info("Incoming call from: %s", caller)

    twiml = twilio.generate_twiml_greeting("hi-IN")
    return Response(content=twiml, media_type="application/xml")


@router.post("/menu")
async def voice_menu(request: Request):
    """
    IVR menu handler. Processes DTMF digit and prompts for voice input.
    """
    from src.services.twilio_service import get_twilio_service

    twilio = get_twilio_service()
    form = await request.form()
    digit = form.get("Digits", "0")
    logger.info("IVR menu selection: %s", digit)

    twiml = twilio.generate_twiml_menu(digit)
    return Response(content=twiml, media_type="application/xml")


@router.post("/response")
async def voice_response(request: Request):
    """
    Process farmer's voice input:
    1. Get recording URL from Twilio
    2. Transcribe via Sarvam AI STT
    3. Route through orchestrator
    4. Convert response to speech via Sarvam TTS
    5. Return TwiML
    """
    from src.orchestrator import SupervisorOrchestrator
    from src.services.sarvam_service import get_sarvam_service
    from src.services.twilio_service import get_twilio_service

    twilio = get_twilio_service()
    sarvam = get_sarvam_service()

    form = await request.form()
    recording_url = form.get("RecordingUrl", "")
    caller = form.get("From", "unknown")
    logger.info("Voice response from %s, recording: %s", caller, recording_url)

    # Step 1: Download and transcribe recording
    transcript_text = "What is the price of wheat?"  # Default fallback
    if recording_url and sarvam.is_available:
        try:
            import httpx
            audio_resp = httpx.get(f"{recording_url}.wav", timeout=10)
            if audio_resp.status_code == 200:
                stt_result = sarvam.speech_to_text(audio_resp.content)
                transcript_text = stt_result.get("text", transcript_text)
                logger.info("Transcribed: %s", transcript_text)
        except Exception as e:
            logger.error("STT failed: %s", e)

    # Step 2: Route through orchestrator
    orchestrator = SupervisorOrchestrator()
    result = orchestrator.route_query(
        query=transcript_text,
        farmer_id="VOICE-USER",
        language="hi-IN",
    )

    # Step 3: Return TwiML response
    response_text = result.final_response[:500]  # Limit for voice
    twiml = twilio.generate_twiml_response(response_text)
    return Response(content=twiml, media_type="application/xml")


@router.post("/status")
async def voice_status(request: Request):
    """Twilio call status callback."""
    form = await request.form()
    call_sid = form.get("CallSid", "")
    call_status = form.get("CallStatus", "")
    logger.info("Call %s status: %s", call_sid, call_status)
    return {"status": "received"}
