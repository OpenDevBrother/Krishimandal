"""
KrishiMandal — Supply Chain Optimization Agent
Plans harvest logistics, coordinates collection routes,
grades crop quality, and recommends market channels.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from src.config import settings
from src.models import (
    AgentResponse,
    HarvestPlan,
    MarketOption,
    NetRealization,
)

logger = logging.getLogger(__name__)


class SupplyChainAgent:
    """Agent responsible for harvest planning and market logistics."""

    NAME = "supply_chain"

    def __init__(self):
        from src.dummy_data import (
            dummy_harvest_plan,
            dummy_market_options,
            dummy_net_realization,
        )
        self._dummy_harvest_plan = dummy_harvest_plan
        self._dummy_market_options = dummy_market_options
        self._dummy_net_realization = dummy_net_realization

    # ── Public methods ───────────────────────────────────────────────────

    def generate_harvest_plan(self, farm_id: str, crop: str = "wheat") -> HarvestPlan:
        """Create a pre-harvest logistics plan."""
        if settings.USE_DUMMY_DATA:
            return self._dummy_harvest_plan(farm_id, crop)
        return self._dummy_harvest_plan(farm_id, crop)

    def recommend_markets(self, crop: str) -> List[MarketOption]:
        """Rank nearby mandis by expected net realisation."""
        if settings.USE_DUMMY_DATA:
            return self._dummy_market_options(crop)
        return self._dummy_market_options(crop)

    def grade_quality(self, image_url: str) -> Dict[str, Any]:
        """Simulate quality grading via computer vision."""
        import random
        grade = random.choice(["A", "B"])
        return {
            "grade": grade,
            "confidence": round(random.uniform(0.7, 0.95), 2),
            "moisture_pct": round(random.uniform(10, 16), 1),
            "defect_pct": round(random.uniform(0, 8), 1),
            "premium_eligible": grade == "A",
        }

    # ── Agent interface (called by Supervisor) ───────────────────────────

    def handle_query(self, query: str, farmer_id: str, **ctx) -> AgentResponse:
        query_lower = query.lower()
        farm_id = f"FARM-{farmer_id}"
        crop = ctx.get("crop", "wheat")

        # Harvest plan
        if any(w in query_lower for w in ["harvest", "plan", "logistics", "katai", "काटना", "योजना"]):
            plan = self.generate_harvest_plan(farm_id, crop)
            lines = [
                f"🌾 Harvest Plan for {plan.farm_id}",
                f"  Date: {plan.harvest_date.isoformat()}",
                f"  Expected yield: {plan.expected_yield_quintals} quintals (Grade {plan.quality_grade.value})",
                f"  Labour needed: {plan.labor_required} persons",
                f"  Target markets: {', '.join(plan.target_markets)}",
                f"  Storage advice: {plan.storage_recommendation}",
                "",
                "Recommendations:",
            ]
            lines.extend(f"  • {r}" for r in plan.recommendations)
            return AgentResponse(
                agent_name=self.NAME,
                response_text="\n".join(lines),
                data=plan.model_dump(mode="json"),
                confidence=0.82,
            )

        # Market comparison
        if any(w in query_lower for w in ["market", "mandi", "मंडी", "where", "sell", "best"]):
            options = self.recommend_markets(crop)
            lines = [f"🏪 Top markets for {crop.title()}:"]
            for i, o in enumerate(options, 1):
                lines.append(
                    f"  {i}. {o.mandi_name} ({o.distance_km} km) — "
                    f"₹{o.expected_price:,.0f}/qtl, fee {o.market_fee_pct}%, "
                    f"Net ₹{o.net_realization:,.0f}/20qtl. "
                    f"Payment: {o.payment_reliability}."
                )
            return AgentResponse(
                agent_name=self.NAME,
                response_text="\n".join(lines),
                data={"markets": [o.model_dump() for o in options]},
                confidence=0.8,
            )

        # Quality grading
        if any(w in query_lower for w in ["quality", "grade", "photo", "गुणवत्ता"]):
            image_url = ctx.get("image_url", "")
            result = self.grade_quality(image_url)
            resp_text = (
                f"Quality grade: {result['grade']} (confidence {result['confidence']:.0%}). "
                f"Moisture: {result['moisture_pct']}%, Defects: {result['defect_pct']}%. "
                f"{'Premium-eligible ✓' if result['premium_eligible'] else 'Standard grade'}"
            )
            return AgentResponse(agent_name=self.NAME, response_text=resp_text, data=result, confidence=result["confidence"])

        # Default: short supply chain summary
        plan = self.generate_harvest_plan(farm_id, crop)
        options = self.recommend_markets(crop)
        best = options[0] if options else None
        resp_text = (
            f"Harvest expected on {plan.harvest_date.isoformat()} with ~{plan.expected_yield_quintals} quintals. "
            f"Best market: {best.mandi_name if best else 'N/A'} (₹{best.expected_price:,.0f}/qtl) "
            f"— {best.distance_km} km away. "
            f"Ask for a full harvest plan or market comparison for details."
        )
        return AgentResponse(agent_name=self.NAME, response_text=resp_text, data=plan.model_dump(mode="json"), confidence=0.78)
