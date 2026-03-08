"""
KrishiMandal — Scheme & Credit Navigator Agent
Matches farmers to government schemes, processes documents,
and computes alternative credit scores.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from src.config import settings
from src.models import (
    AgentResponse,
    CreditScore,
    LenderMatch,
    SchemeMatch,
)

logger = logging.getLogger(__name__)


class SchemeCreditAgent:
    """Agent responsible for scheme discovery, eligibility, and credit scoring."""

    NAME = "scheme_credit"

    def __init__(self):
        from src.dummy_data import (
            dummy_credit_score,
            dummy_lender_matches,
            dummy_scheme_matches,
        )
        self._dummy_scheme_matches = dummy_scheme_matches
        self._dummy_credit_score = dummy_credit_score
        self._dummy_lender_matches = dummy_lender_matches

    # ── Public methods ───────────────────────────────────────────────────

    def match_schemes(self, farmer_id: str) -> List[SchemeMatch]:
        """Return government schemes the farmer is eligible for."""
        if settings.USE_DUMMY_DATA:
            return self._dummy_scheme_matches()
        return self._dummy_scheme_matches()

    def compute_credit_score(self, farmer_id: str) -> CreditScore:
        """Calculate alternative credit score based on farm activity."""
        if settings.USE_DUMMY_DATA:
            return self._dummy_credit_score(farmer_id)
        return self._dummy_credit_score(farmer_id)

    def match_lenders(self, farmer_id: str) -> List[LenderMatch]:
        """Find suitable lenders for the farmer's credit profile."""
        if settings.USE_DUMMY_DATA:
            return self._dummy_lender_matches()
        return self._dummy_lender_matches()

    def extract_document(self, image_url: str) -> Dict[str, Any]:
        """Simulate OCR extraction from a document photo.
        In production calls Amazon Textract.
        """
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
            "language_detected": "Marathi",
        }

    # ── Agent interface (called by Supervisor) ───────────────────────────

    def handle_query(self, query: str, farmer_id: str, **ctx) -> AgentResponse:
        query_lower = query.lower()

        # Scheme matching
        if any(w in query_lower for w in ["scheme", "yojana", "योजना", "subsidy", "benefit", "सरकारी"]):
            matches = self.match_schemes(farmer_id)
            lines = []
            for m in matches:
                missing = f" (Missing: {', '.join(m.missing_criteria)})" if m.missing_criteria else ""
                lines.append(
                    f"✅ {m.scheme_name} — Eligibility {m.eligibility_score:.0%}, "
                    f"Benefit ₹{m.benefits_inr:,.0f}"
                    f"{missing}"
                )
            intro = f"Found {len(matches)} schemes you may be eligible for:\n"
            resp_text = intro + "\n".join(lines)
            return AgentResponse(
                agent_name=self.NAME,
                response_text=resp_text,
                data={"schemes": [m.model_dump(mode="json") for m in matches]},
                confidence=0.85,
                has_actions=True,
                actions=[{"id": m.scheme_id, "label": f"Apply: {m.scheme_name[:25]}"} for m in matches[:3]],
            )

        # Credit score
        if any(w in query_lower for w in ["credit", "loan", "rin", "ऋण", "score", "lender", "bank"]):
            score = self.compute_credit_score(farmer_id)
            lenders = self.match_lenders(farmer_id)
            score_lines = [
                f"Your KrishiMandal Credit Score: {score.score:.0f}/100",
                "Components:",
            ]
            for k, v in score.components.items():
                score_lines.append(f"  • {k.replace('_', ' ').title()}: {v:.1f}")

            score_lines.append("\nMatched lenders:")
            for l in lenders:
                collateral = "No collateral" if not l.collateral_required else "Collateral needed"
                score_lines.append(
                    f"  🏦 {l.lender_name} — {l.interest_rate}% p.a., "
                    f"up to ₹{l.max_amount:,.0f}, {l.tenure_months} months. {collateral}."
                )

            return AgentResponse(
                agent_name=self.NAME,
                response_text="\n".join(score_lines),
                data={
                    "credit_score": score.model_dump(mode="json"),
                    "lenders": [l.model_dump() for l in lenders],
                },
                confidence=0.82,
            )

        # Document OCR
        if any(w in query_lower for w in ["document", "upload", "ocr", "dastaawaiz", "दस्तावेज़"]):
            image_url = ctx.get("image_url", "")
            result = self.extract_document(image_url)
            fields = result["extracted_fields"]
            resp_text = (
                f"Document type: {result['document_type']} "
                f"(confidence {result['confidence']:.0%}). "
                f"Owner: {fields['owner_name']}, Survey: {fields['survey_number']}, "
                f"Village: {fields['village']}, Area: {fields['area_hectares']} ha."
            )
            return AgentResponse(agent_name=self.NAME, response_text=resp_text, data=result, confidence=result["confidence"])

        # Default: brief eligibility summary
        matches = self.match_schemes(farmer_id)
        total_benefits = sum(m.benefits_inr for m in matches)
        resp_text = (
            f"You are potentially eligible for {len(matches)} government schemes "
            f"with combined benefits of ₹{total_benefits:,.0f}. "
            f"Say 'show schemes' for the full list, or 'credit score' to check loan eligibility."
        )
        return AgentResponse(agent_name=self.NAME, response_text=resp_text, data={"scheme_count": len(matches), "total_benefits": total_benefits}, confidence=0.8)
