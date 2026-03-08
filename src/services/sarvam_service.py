"""
KrishiMandal — Sarvam AI service for multilingual STT/TTS.
Provides speech-to-text, text-to-speech, and language detection
for all 22 scheduled Indian languages.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.config import settings

logger = logging.getLogger(__name__)


class SarvamService:
    """Client for Sarvam AI Saaras v3 APIs."""

    def __init__(self):
        self.is_available = bool(settings.SARVAM_AI_API_KEY)
        self.base_url = settings.SARVAM_AI_BASE_URL.rstrip("/")
        self.api_key = settings.SARVAM_AI_API_KEY

        if self.is_available:
            logger.info("SarvamService initialized (base_url=%s)", self.base_url)
        else:
            logger.info("Sarvam AI not configured. STT/TTS features disabled.")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def speech_to_text(
        self, audio_bytes: bytes, language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convert speech audio to text using Sarvam AI Saaras v3.
        Returns: {text, language_detected, confidence}
        """
        if not self.is_available:
            return self._stt_fallback()

        try:
            import httpx

            files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
            data = {}
            if language:
                data["language"] = language

            response = httpx.post(
                f"{self.base_url}/speech-to-text",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files=files,
                data=data,
                timeout=10.0,
            )
            response.raise_for_status()
            result = response.json()
            return {
                "text": result.get("transcript", ""),
                "language_detected": result.get("language_code", language or "hi-IN"),
                "confidence": result.get("confidence", 0.8),
            }
        except Exception as e:
            logger.error("Sarvam STT failed: %s", e)
            return self._stt_fallback()

    def text_to_speech(
        self, text: str, language: str = "hi-IN", voice: Optional[str] = None
    ) -> bytes:
        """
        Convert text to speech audio using Sarvam AI TTS.
        Returns: audio bytes (WAV format).
        """
        if not self.is_available:
            return b""

        try:
            import httpx

            payload = {
                "text": text,
                "language": language,
            }
            if voice:
                payload["voice"] = voice

            response = httpx.post(
                f"{self.base_url}/text-to-speech",
                headers=self._headers(),
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error("Sarvam TTS failed: %s", e)
            return b""

    def detect_language(self, text: str) -> str:
        """Detect the language of a text string."""
        if not self.is_available:
            return "hi-IN"

        try:
            import httpx

            response = httpx.post(
                f"{self.base_url}/detect-language",
                headers=self._headers(),
                json={"text": text},
                timeout=5.0,
            )
            response.raise_for_status()
            return response.json().get("language_code", "hi-IN")
        except Exception as e:
            logger.warning("Language detection failed: %s", e)
            return "hi-IN"

    def _stt_fallback(self) -> Dict[str, Any]:
        return {
            "text": "",
            "language_detected": "hi-IN",
            "confidence": 0.0,
            "error": "Sarvam AI not available. Configure SARVAM_AI_API_KEY.",
        }


# Singleton
_sarvam: SarvamService | None = None


def get_sarvam_service() -> SarvamService:
    global _sarvam
    if _sarvam is None:
        _sarvam = SarvamService()
    return _sarvam
