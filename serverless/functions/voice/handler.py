"""
KrishiMandal Serverless — Voice Lambda (Sarvam AI Saaras v3 + Bulbul v3)
Provides STT and TTS endpoints for multilingual voice assistant.
"""
import base64
import json
import logging
import os
from urllib import request as urllib_request, parse as urllib_parse

from common.response import ok, bad_request, error
from common.fallback import fallback_to_ec2

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "")
SARVAM_BASE = "https://api.sarvam.ai"

# Language code mapping: frontend short codes → BCP-47
LANG_MAP = {
    "en": "en-IN", "hi": "hi-IN", "bn": "bn-IN", "te": "te-IN",
    "mr": "mr-IN", "ta": "ta-IN", "gu": "gu-IN", "kn": "kn-IN",
    "ml": "ml-IN", "or": "od-IN", "pa": "pa-IN", "as": "as-IN",
    "mai": "mai-IN", "sa": "sa-IN", "ne": "ne-IN", "sd": "sd-IN",
    "ks": "ks-IN", "doi": "doi-IN", "kok": "kok-IN", "mni": "mni-IN",
    "sat": "sat-IN", "ur": "ur-IN",
}

# TTS supported languages (Bulbul v3 supports fewer than STT)
TTS_SUPPORTED = {
    "en-IN", "hi-IN", "bn-IN", "te-IN", "mr-IN", "ta-IN",
    "gu-IN", "kn-IN", "ml-IN", "od-IN", "pa-IN",
}


def _stt(audio_b64: str, language_code: str | None = None) -> dict:
    """Call Sarvam STT (Saaras v3) with base64-encoded audio."""
    import io
    import email.mime.multipart
    import email.mime.base
    import email.mime.text

    audio_bytes = base64.b64decode(audio_b64)

    # Build multipart/form-data manually (no requests/httpx in Lambda)
    boundary = "----SarvamBoundary7MA4YWxkTrZu0gW"
    body_parts = []

    # Audio file part
    body_parts.append(f"--{boundary}")
    body_parts.append('Content-Disposition: form-data; name="file"; filename="audio.webm"')
    body_parts.append("Content-Type: audio/webm")
    body_parts.append("")

    # Model part
    model_part = f"--{boundary}\r\nContent-Disposition: form-data; name=\"model\"\r\n\r\nsaaras:v3"

    # Language part (optional)
    lang_part = ""
    if language_code:
        lang_part = f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"language_code\"\r\n\r\n{language_code}"

    # Build raw body
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="audio.webm"\r\n'
        f"Content-Type: audio/webm\r\n\r\n"
    ).encode("utf-8")
    body += audio_bytes
    body += f"\r\n{model_part}{lang_part}\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib_request.Request(
        f"{SARVAM_BASE}/speech-to-text",
        data=body,
        headers={
            "api-subscription-key": SARVAM_API_KEY,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )

    with urllib_request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read().decode())

    return {
        "transcript": result.get("transcript", ""),
        "language_code": result.get("language_code", language_code or "hi-IN"),
        "confidence": result.get("language_probability", 0.8),
    }


def _tts(text: str, language_code: str = "hi-IN", speaker: str = "shubh") -> str:
    """Call Sarvam TTS (Bulbul v3) and return base64 audio."""
    # Fall back to Hindi if language not supported by TTS
    if language_code not in TTS_SUPPORTED:
        language_code = "hi-IN"

    payload = json.dumps({
        "text": text[:2500],
        "target_language_code": language_code,
        "model": "bulbul:v3",
        "speaker": speaker,
        "speech_sample_rate": 22050,
        "output_audio_codec": "mp3",
    }).encode("utf-8")

    req = urllib_request.Request(
        f"{SARVAM_BASE}/text-to-speech",
        data=payload,
        headers={
            "api-subscription-key": SARVAM_API_KEY,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib_request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read().decode())

    audios = result.get("audios", [])
    if audios:
        return audios[0]
    return ""


def handler(event, context):
    """Lambda handler for POST /voice/stt and POST /voice/tts."""
    try:
        path = event.get("path", "")
        method = event.get("httpMethod", "POST")

        if method == "OPTIONS":
            return ok({})

        if not SARVAM_API_KEY:
            return error("Sarvam API key not configured.")

        body = json.loads(event.get("body", "{}") or "{}")

        # ── Speech-to-Text ──
        if path.endswith("/voice/stt"):
            audio_b64 = body.get("audio")
            if not audio_b64:
                return bad_request("audio (base64) is required.")
            language = body.get("language")
            lang_code = LANG_MAP.get(language, language) if language else None
            result = _stt(audio_b64, lang_code)
            return ok(result)

        # ── Text-to-Speech ──
        elif path.endswith("/voice/tts"):
            text = body.get("text", "")
            if not text:
                return bad_request("text is required.")
            language = body.get("language", "hi")
            lang_code = LANG_MAP.get(language, language)
            speaker = body.get("speaker", "shubh")
            audio_b64 = _tts(text, lang_code, speaker)
            return ok({"audio": audio_b64, "content_type": "audio/mp3"})

        else:
            return bad_request(f"Unknown voice path: {path}")

    except Exception as e:
        logger.error("Voice handler failed: %s", e, exc_info=True)
        return error(str(e))
