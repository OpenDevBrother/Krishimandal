"""
KrishiMandal — OCR service for document text extraction.
Returns structured extracted_fields based on document type.
In production, this would call Amazon Textract.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class OCRService:
    """Extract text from document images."""

    def extract_text(self, image_path: str, document_name: str = "") -> Dict[str, Any]:
        doc = document_name.lower()

        if "aadhaar" in doc or "aadhar" in doc or "adhaar" in doc:
            return {
                "document_type": "Aadhaar Card",
                "extracted_fields": {
                    "name": "Anjali Kumari",
                    "dob": "18/09/1999",
                    "gender": "Female",
                    "aadhaar_number": "2268-1622-3671",
                    "phone": "9582539507",
                    "address": {
                        "raw": "D/O Mukesh Kumar, H. No. E-376, Street No. 15, Ashok Nagar, Shahdara, North East Delhi - 110093",
                        "village": "Ashok Nagar",
                        "district": "Shahdara",
                        "state": "Delhi",
                        "pincode": "110093",
                    },
                },
                "confidence": 0.95,
                "method": "ocr",
                "image_path": image_path,
            }

        if "bank" in doc or "passbook" in doc:
            return {
                "document_type": "Bank Passbook",
                "extracted_fields": {
                    "name": "Rajesh Patil",
                    "bank_account": "31245678901",
                    "ifsc_code": "SBIN0001234",
                    "bank_name": "State Bank of India",
                },
                "confidence": 0.88,
                "method": "ocr",
                "image_path": image_path,
            }

        if "domicile" in doc or "address" in doc or "residence" in doc:
            return {
                "document_type": "Domicile Certificate",
                "extracted_fields": {
                    "name": "Rajesh Patil",
                    "address": {
                        "raw": "42, Shivaji Nagar, Baramati, Pune, Maharashtra 413102",
                        "village": "Baramati",
                        "district": "Pune",
                        "state": "Maharashtra",
                        "pincode": "413102",
                    },
                },
                "confidence": 0.90,
                "method": "ocr",
                "image_path": image_path,
            }

        # Default: Land Record
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
            "method": "ocr",
            "image_path": image_path,
        }


# Singleton
_ocr: OCRService | None = None


def get_ocr_service() -> OCRService:
    global _ocr
    if _ocr is None:
        _ocr = OCRService()
    return _ocr
