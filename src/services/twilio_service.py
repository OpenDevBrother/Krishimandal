"""
KrishiMandal — Twilio service for voice calls and WhatsApp.
Generates TwiML responses and sends messages.
Gracefully degrades if Twilio credentials are not configured.
"""
from __future__ import annotations

import logging
from typing import Optional

from src.config import settings

logger = logging.getLogger(__name__)


class TwilioService:
    """Wrapper around the Twilio API for voice and messaging."""

    def __init__(self):
        self.is_available = False
        self.client = None

        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            try:
                from twilio.rest import Client
                self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                self.is_available = True
                logger.info("TwilioService initialized successfully.")
            except ImportError:
                logger.warning("twilio package not installed. Voice/SMS features disabled.")
            except Exception as e:
                logger.warning("Twilio initialization failed: %s", e)
        else:
            logger.info("Twilio credentials not configured. Voice/SMS features disabled.")

    def generate_twiml_greeting(self, language: str = "hi-IN") -> str:
        """Generate TwiML for incoming call greeting."""
        greetings = {
            "hi-IN": "नमस्ते! कृषिमंडल में आपका स्वागत है। कृपया विकल्प चुनें।",
            "mr-IN": "नमस्कार! कृषिमंडल मध्ये आपले स्वागत आहे.",
            "en-IN": "Welcome to KrishiMandal. Please choose an option.",
        }
        text = greetings.get(language, greetings["en-IN"])
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="{language}">{text}</Say>
    <Gather numDigits="1" action="/voice/menu" method="POST">
        <Say language="{language}">
            Press 1 for Farm Status.
            Press 2 for Market Prices.
            Press 3 for Government Schemes.
            Press 4 for Learning.
        </Say>
    </Gather>
</Response>"""

    def generate_twiml_menu(self, digit: str, language: str = "hi-IN") -> str:
        """Generate TwiML response based on IVR menu selection."""
        menu_map = {
            "1": ("Farm Status", "Tell me about your farm. Please speak after the beep."),
            "2": ("Market Prices", "Which crop price would you like to know? Please speak."),
            "3": ("Government Schemes", "I will check which schemes you are eligible for. Please speak."),
            "4": ("Learning", "What would you like to learn about? Please speak."),
        }
        title, prompt = menu_map.get(digit, ("General", "Please speak your question."))
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="{language}">{title}. {prompt}</Say>
    <Record maxLength="30" action="/voice/response" method="POST"
            recordingStatusCallback="/voice/status" />
</Response>"""

    def generate_twiml_response(self, text: str, language: str = "hi-IN") -> str:
        """Generate TwiML that speaks a text response."""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="{language}">{text}</Say>
    <Say language="{language}">Thank you for using KrishiMandal. Goodbye.</Say>
</Response>"""

    def send_sms(self, to: str, body: str) -> Optional[str]:
        """Send an SMS message. Returns message SID or None."""
        if not self.is_available or not settings.TWILIO_PHONE_NUMBER:
            logger.warning("Cannot send SMS — Twilio not configured.")
            return None
        try:
            msg = self.client.messages.create(
                body=body,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=to,
            )
            return msg.sid
        except Exception as e:
            logger.error("SMS send failed: %s", e)
            return None

    def send_whatsapp(self, to: str, body: str) -> Optional[str]:
        """Send a WhatsApp message. Returns message SID or None."""
        if not self.is_available or not settings.TWILIO_WHATSAPP_NUMBER:
            logger.warning("Cannot send WhatsApp — Twilio not configured.")
            return None
        try:
            msg = self.client.messages.create(
                body=body,
                from_=f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}",
                to=f"whatsapp:{to}",
            )
            return msg.sid
        except Exception as e:
            logger.error("WhatsApp send failed: %s", e)
            return None


# Singleton
_twilio: TwilioService | None = None


def get_twilio_service() -> TwilioService:
    global _twilio
    if _twilio is None:
        _twilio = TwilioService()
    return _twilio
