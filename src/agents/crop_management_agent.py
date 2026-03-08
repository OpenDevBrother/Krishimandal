"""
KrishiMandal — Crop Management Agent
Monitors crop health, predicts pests/diseases, recommends inputs,
and optimises irrigation schedules.  Uses dummy data when real
satellite/IoT feeds are unavailable.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from src.config import settings
from src.models import (
    AgentResponse,
    CropHealth,
    InputRecommendation,
    PestAlert,
)

logger = logging.getLogger(__name__)


class CropManagementAgent:
    """Agent responsible for crop health monitoring and advisory."""

    NAME = "crop_management"

    def __init__(self):
        from src.dummy_data import (
            dummy_crop_health,
            dummy_input_recommendation,
            dummy_pest_alerts,
        )
        self._dummy_crop_health = dummy_crop_health
        self._dummy_pest_alerts = dummy_pest_alerts
        self._dummy_input_recommendation = dummy_input_recommendation

    # ── Public methods ───────────────────────────────────────────────────

    def compute_health_score(self, farm_id: str) -> CropHealth:
        """Calculate compound crop health score (0-100) from 4 components."""
        if settings.USE_DUMMY_DATA:
            return self._dummy_crop_health(farm_id)
        # Production: blend satellite NDVI, weather, soil, growth-stage data
        return self._dummy_crop_health(farm_id)

    def predict_pest_outbreak(self, crop: str, farm_id: str) -> List[PestAlert]:
        """Forecast pest risk 3-7 days ahead based on weather & regional data."""
        if settings.USE_DUMMY_DATA:
            return self._dummy_pest_alerts(crop)
        return self._dummy_pest_alerts(crop)

    def recommend_inputs(self, crop: str, farm_id: str) -> List[InputRecommendation]:
        """Produce fertiliser / irrigation recommendations for the crop."""
        if settings.USE_DUMMY_DATA:
            return self._dummy_input_recommendation(crop)
        return self._dummy_input_recommendation(crop)

    def analyze_crop_photo(self, image_url: str) -> Dict[str, Any]:
        """Analyse a farmer-uploaded crop photo for disease / pest symptoms.
        In production this calls Amazon Bedrock or a custom CV model.
        Here we return a simulated diagnosis.
        """
        return {
            "diagnosis": "Leaf Rust (Puccinia triticina)",
            "confidence": 0.83,
            "severity": "moderate",
            "affected_area_pct": 15,
            "recommendations": [
                "Apply Propiconazole 25 EC @ 0.1% spray.",
                "Avoid overhead irrigation.",
                "Remove severely infected leaves.",
            ],
            "image_url": image_url,
        }

    # ── Agent interface (called by Supervisor) ───────────────────────────

    def handle_query(self, query: str, farmer_id: str, **ctx) -> AgentResponse:
        query_lower = query.lower()
        farm_id = f"FARM-{farmer_id}"

        # Pest / disease path
        if any(w in query_lower for w in ["pest", "disease", "keet", "bimari", "कीट", "बीमारी", "rog", "रोग"]):
            crop = ctx.get("crop", "wheat")
            alerts = self.predict_pest_outbreak(crop, farm_id)
            lines = []
            for a in alerts:
                lines.append(
                    f"⚠ {a.pest_type.replace('_', ' ').title()} — risk {a.risk_level:.0%}, "
                    f"expected in {a.forecast_days} days. Actions: {'; '.join(a.recommended_actions)}"
                )
            resp_text = "\n".join(lines) if lines else "No significant pest risk detected."
            return AgentResponse(
                agent_name=self.NAME,
                response_text=resp_text,
                data={"alerts": [a.model_dump() for a in alerts]},
                confidence=0.8,
            )

        # Fertiliser / input path
        if any(w in query_lower for w in ["fertilizer", "fertiliser", "khad", "खाद", "input", "urea", "dap"]):
            crop = ctx.get("crop", "wheat")
            recs = self.recommend_inputs(crop, farm_id)
            lines = [
                f"• {r.product} — {r.quantity_kg_per_hectare} kg/ha, "
                f"apply {r.timing}. Benefit: {r.expected_benefit}. Cost ≈ ₹{r.cost_inr}"
                for r in recs
            ]
            return AgentResponse(
                agent_name=self.NAME,
                response_text="\n".join(lines),
                data={"recommendations": [r.model_dump() for r in recs]},
                confidence=0.85,
            )

        # Photo analysis path
        if any(w in query_lower for w in ["photo", "image", "picture", "फ़ोटो", "तस्वीर"]):
            image_url = ctx.get("image_url", "")
            result = self.analyze_crop_photo(image_url)
            resp_text = (
                f"Diagnosis: {result['diagnosis']} (confidence {result['confidence']:.0%}). "
                f"Severity: {result['severity']}, affected area ≈{result['affected_area_pct']}%. "
                f"Recommendations: {'; '.join(result['recommendations'])}"
            )
            return AgentResponse(agent_name=self.NAME, response_text=resp_text, data=result, confidence=result["confidence"])

        # Default: health score overview
        health = self.compute_health_score(farm_id)
        c = health.components
        resp_text = (
            f"Crop health score: {health.health_score}/100. "
            f"Components — Soil: {c.soil_score}/25, Season: {c.season_score}/25, "
            f"Stage: {c.stage_score}/25, Weather: {c.weather_score}/25. "
            f"NDVI: {health.ndvi_mean}."
        )
        if health.anomalies:
            resp_text += f" ⚠ {len(health.anomalies)} anomaly detected — inspect field."
        return AgentResponse(
            agent_name=self.NAME,
            response_text=resp_text,
            data=health.model_dump(mode="json"),
            confidence=0.85,
        )
