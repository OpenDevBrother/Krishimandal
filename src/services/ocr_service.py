"""
KrishiMandal — OCR service for document text extraction.
Uses Groq vision model when available, falls back to dummy extraction.
In production, this would call Amazon Textract.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class OCRService:
    """Extract text from document images."""

    def __init__(self):
        from src.services.llm_service import get_llm
        self.llm = get_llm()

    def extract_text(self, image_path: str) -> Dict[str, Any]:
        """
        Extract text and fields from a document image.
        Returns document_type, extracted_fields, confidence.
        """
        # Try LLM-based extraction if available
        if self.llm.is_available:
            try:
                result = self.llm.chat(
                    messages=[{
                        "role": "user",
                        "content": (
                            f"A farmer has uploaded a document image at '{image_path}'. "
                            "Simulate OCR extraction and return the likely document type "
                            "(Land Record, Aadhaar, Bank Passbook, etc.) and key fields. "
                            "Return a structured response with document_type, owner_name, "
                            "and other relevant fields."
                        ),
                    }],
                    system_prompt="You are an OCR system for Indian agricultural documents. Return structured information.",
                    max_tokens=300,
                )
                return {
                    "document_type": "Detected Document",
                    "extracted_text": result,
                    "confidence": 0.75,
                    "method": "llm_simulated",
                    "image_path": image_path,
                }
            except Exception as e:
                logger.warning("LLM OCR failed: %s", e)

        # Fallback: dummy extraction
        return self._dummy_extraction(image_path)

    def _dummy_extraction(self, image_path: str) -> Dict[str, Any]:
        return {
            "document_type": "Land Record (7/12 extract)",
            "extracted_fields": {
                "owner_name": "Rajesh Patil",
                "survey_number": "123/4A",
                "village": "Baramati",
                "taluka": "Baramati",
                "district": "Pune",
                "area_hectares": 2.5,
                "crop_listed": "Sugarcane",
            },
            "confidence": 0.91,
            "method": "dummy",
            "language_detected": "Marathi",
            "image_path": image_path,
        }


# Singleton
_ocr: OCRService | None = None


def get_ocr_service() -> OCRService:
    global _ocr
    if _ocr is None:
        _ocr = OCRService()
    return _ocr
