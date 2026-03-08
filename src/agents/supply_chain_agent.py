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
        """Create a pre-harvest logistics plan using farm profile + weather."""
        if settings.USE_DUMMY_DATA:
            return self._dummy_harvest_plan(farm_id, crop)
        return self._generate_real_harvest_plan(farm_id, crop)

    def _generate_real_harvest_plan(self, farm_id: str, crop: str) -> HarvestPlan:
        """Generate harvest plan from farm profile, growth stage, and weather."""
        from src.database import SessionLocal
        from src.repositories import get_farm, get_latest_farm_state
        from datetime import date, timedelta
        import json

        db = SessionLocal()
        try:
            farm = get_farm(db, farm_id)
            if not farm:
                return self._dummy_harvest_plan(farm_id, crop)

            # Get current crop details
            current_crops = [c for c in farm.crops if c.is_current and c.crop_type == crop]
            if not current_crops:
                current_crops = [c for c in farm.crops if c.is_current]
            if not current_crops:
                return self._dummy_harvest_plan(farm_id, crop)

            crop_record = current_crops[0]
            harvest_date = crop_record.expected_harvest or (date.today() + timedelta(days=30))
            area = crop_record.area_hectares

            # Yield estimates (quintals/ha by crop)
            yield_map = {
                "wheat": 40, "cotton": 20, "soybean": 22, "sugarcane": 800,
                "jowar": 30, "bajra": 25, "tur": 12, "gram": 15,
                "onion": 200, "rice": 45,
            }
            yield_per_ha = yield_map.get(crop_record.crop_type, 25)
            total_yield = round(yield_per_ha * area, 1)

            # Weather-based recommendations
            recommendations = [
                f"Expected yield: {total_yield} quintals from {area} ha",
                "Arrange labour 1 week before harvest date",
            ]

            state_record = get_latest_farm_state(db, farm_id)
            if state_record and state_record.weather_json:
                try:
                    weather = json.loads(state_record.weather_json)
                    if weather.get("rainfall_mm", 0) > 5:
                        recommendations.append("Rain expected — delay harvest by 2-3 days if possible")
                    if weather.get("humidity_pct", 0) > 80:
                        recommendations.append("High humidity — ensure proper drying after harvest")
                except (json.JSONDecodeError, KeyError):
                    pass

            recommendations.append("Arrange transport to mandi 1 day before selling")

            # Get best markets from real prices
            target_markets = ["Pune APMC", "Nashik APMC", "Nagpur APMC"]
            try:
                from src.repositories import get_price_history
                recent_prices = get_price_history(db, crop_record.crop_type, None, days=7)
                if recent_prices:
                    mandis = list(set(r.mandi for r in recent_prices))[:3]
                    if mandis:
                        target_markets = mandis
            except Exception:
                pass

            from src.models import HarvestPlan, QualityGrade
            return HarvestPlan(
                farm_id=farm_id,
                harvest_date=harvest_date,
                expected_yield_quintals=total_yield,
                quality_grade=QualityGrade.B if crop_record.health_score >= 70 else QualityGrade.C,
                labor_required=max(2, int(area * 3)),
                target_markets=target_markets,
                storage_recommendation="Store in dry, ventilated area. Use moisture-proof bags." if total_yield > 30 else "Sell within 1 week of harvest.",
                recommendations=recommendations,
            )
        except Exception as e:
            logger.warning("Real harvest plan failed for %s: %s", farm_id, e)
            return self._dummy_harvest_plan(farm_id, crop)
        finally:
            db.close()

    def recommend_markets(self, crop: str) -> List[MarketOption]:
        """Rank nearby mandis by real prices from DB."""
        if settings.USE_DUMMY_DATA:
            return self._dummy_market_options(crop)
        return self._recommend_markets_from_db(crop)

    def _recommend_markets_from_db(self, crop: str) -> List[MarketOption]:
        """Use real price data to rank mandis."""
        from src.database import SessionLocal
        from src.repositories import get_price_history

        db = SessionLocal()
        try:
            records = get_price_history(db, crop, None, days=7)
            if not records:
                return self._dummy_market_options(crop)

            # Group by mandi, get average price
            mandi_data: dict = {}
            for r in records:
                if r.mandi not in mandi_data:
                    mandi_data[r.mandi] = {"prices": [], "latest": r.price}
                mandi_data[r.mandi]["prices"].append(r.price)

            options = []
            # Dummy distances (would come from geo calculation in production)
            import random
            for mandi, data in sorted(mandi_data.items(), key=lambda x: -max(x[1]["prices"])):
                avg_price = sum(data["prices"]) / len(data["prices"])
                distance = round(random.uniform(15, 80), 0)
                market_fee = 2.0  # Standard APMC fee
                gross = avg_price * 20  # 20 quintals
                transport = distance * 15  # Rs 15/km
                fee = gross * market_fee / 100
                net = gross - transport - fee

                options.append(MarketOption(
                    mandi_name=mandi,
                    distance_km=distance,
                    expected_price=round(avg_price, 0),
                    market_fee_pct=market_fee,
                    net_realization=round(net, 0),
                    payment_reliability="high" if len(data["prices"]) >= 5 else "medium",
                ))

                if len(options) >= 5:
                    break

            return options if options else self._dummy_market_options(crop)
        except Exception as e:
            logger.warning("Market recommendation from DB failed: %s", e)
            return self._dummy_market_options(crop)
        finally:
            db.close()

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
