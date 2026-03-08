"""
KrishiMandal — Mandi Price Predictor Agent
Forecasts crop prices at multiple time horizons (short / medium / long),
recommends sell-or-store decisions, and identifies the best mandi.
Uses e-NAM public data when available, falls back to dummy data.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from src.config import settings
from src.models import (
    AgentResponse,
    MarketDecision,
    NetRealization,
    PriceForecast,
)

logger = logging.getLogger(__name__)


class PricePredictorAgent:
    """Agent responsible for mandi price forecasting and sell/store advice."""

    NAME = "price_predictor"

    def __init__(self):
        from src.dummy_data import (
            dummy_market_decision,
            dummy_net_realization,
            dummy_price_forecast,
        )
        self._dummy_price_forecast = dummy_price_forecast
        self._dummy_market_decision = dummy_market_decision
        self._dummy_net_realization = dummy_net_realization

    # ── Public methods ───────────────────────────────────────────────────

    def forecast_price(self, crop: str, mandi: str | None = None) -> PriceForecast:
        """Return current price + 7-day and 30-day forecasts."""
        if settings.USE_DUMMY_DATA:
            return self._dummy_price_forecast(crop, mandi)
        return self._forecast_from_db(crop, mandi)

    def get_price_history(self, crop: str, mandi: str | None = None, days: int = 30) -> list:
        """Return historical price records from DB."""
        from src.database import SessionLocal
        from src.repositories import get_price_history
        db = SessionLocal()
        try:
            records = get_price_history(db, crop, mandi, days)
            return [
                {"crop": r.crop, "mandi": r.mandi, "price": r.price, "date": r.recorded_at.isoformat()}
                for r in records
            ]
        finally:
            db.close()

    def _forecast_from_db(self, crop: str, mandi: str | None) -> PriceForecast:
        """Build a forecast from historical DB prices."""
        from src.database import SessionLocal
        from src.repositories import get_price_history
        db = SessionLocal()
        try:
            records_7d = get_price_history(db, crop, mandi, days=7)
            records_30d = get_price_history(db, crop, mandi, days=30)
            if not records_7d:
                return self._dummy_price_forecast(crop, mandi)

            current = records_7d[0].price
            avg_7d = sum(r.price for r in records_7d) / len(records_7d)
            avg_30d = sum(r.price for r in records_30d) / len(records_30d) if records_30d else current
            prices = [r.price for r in records_30d] if records_30d else [current]

            if avg_7d > current * 1.02:
                trend = "rising"
            elif avg_7d < current * 0.98:
                trend = "falling"
            else:
                trend = "stable"

            return PriceForecast(
                crop=crop,
                mandi=mandi or records_7d[0].mandi,
                current_price=round(current, 0),
                forecast_7day=round(avg_7d, 0),
                forecast_30day=round(avg_30d, 0),
                confidence_lower=round(min(prices) * 0.95, 0),
                confidence_upper=round(max(prices) * 1.05, 0),
                trend=trend,
                factors=[{"factor": "historical_average", "impact": 0.0, "explanation": "Based on recent price history"}],
            )
        finally:
            db.close()

    def recommend_decision(self, farmer_id: str, crop: str, quantity_quintals: float = 20.0) -> MarketDecision:
        """Sell now / store / wait recommendation based on real price trends."""
        if settings.USE_DUMMY_DATA:
            return self._dummy_market_decision(farmer_id, crop)
        return self._recommend_from_db(farmer_id, crop, quantity_quintals)

    def _recommend_from_db(self, farmer_id: str, crop: str, quantity_quintals: float) -> MarketDecision:
        """Generate sell/store/wait decision from real DB price data."""
        from src.database import SessionLocal
        from src.repositories import get_price_history
        db = SessionLocal()
        try:
            records_7d = get_price_history(db, crop, None, days=7)
            records_30d = get_price_history(db, crop, None, days=30)
            if not records_7d:
                return self._dummy_market_decision(farmer_id, crop)

            current = records_7d[0].price
            avg_7d = sum(r.price for r in records_7d) / len(records_7d)
            avg_30d = sum(r.price for r in records_30d) / len(records_30d) if records_30d else current
            best_mandi = records_7d[0].mandi

            # Find best mandi (highest recent price)
            mandi_prices = {}
            for r in records_7d:
                if r.mandi not in mandi_prices or r.price > mandi_prices[r.mandi]:
                    mandi_prices[r.mandi] = r.price
            if mandi_prices:
                best_mandi = max(mandi_prices, key=mandi_prices.get)
                current = mandi_prices[best_mandi]

            # Decision logic
            if avg_7d > avg_30d * 1.05:
                # Prices rising significantly
                recommendation = "wait"
                timing = "Prices are trending up — consider waiting 1-2 weeks"
                risk = "medium — prices may reverse"
            elif avg_7d < avg_30d * 0.95:
                # Prices falling
                recommendation = "sell_now"
                timing = "Prices are declining — sell within this week"
                risk = "low — avoid further price drops"
            elif current > avg_30d * 1.02:
                # Current price above average
                recommendation = "sell_now"
                timing = "Current price is above 30-day average — good time to sell"
                risk = "low"
            else:
                recommendation = "store_2_weeks"
                timing = "Prices stable — store for 2 weeks and monitor"
                risk = "medium — storage costs apply"

            net = self._calculate_real_net(current, quantity_quintals)
            opportunity_cost = abs(current - avg_30d) * quantity_quintals

            return MarketDecision(
                recommendation=recommendation,
                expected_net_realization=net.net_amount,
                best_mandi=best_mandi,
                timing=timing,
                risk_assessment=risk,
                opportunity_cost=round(opportunity_cost, 0),
            )
        except Exception as e:
            logger.warning("Decision from DB failed: %s", e)
            return self._dummy_market_decision(farmer_id, crop)
        finally:
            db.close()

    def calculate_net_realization(self, quantity_quintals: float = 20.0, crop: str = "wheat") -> NetRealization:
        """Compute net income after transport, fees, and storage."""
        if settings.USE_DUMMY_DATA:
            return self._dummy_net_realization(quantity_quintals)
        return self._calculate_real_net_from_db(crop, quantity_quintals)

    def _calculate_real_net(self, price_per_quintal: float, quantity: float) -> NetRealization:
        """Calculate net realization from a given price."""
        gross = price_per_quintal * quantity
        transport = quantity * 50  # ~Rs 50/quintal transport
        market_fee = gross * 0.02  # 2% APMC market fee
        storage = quantity * 20  # ~Rs 20/quintal handling
        net = gross - transport - market_fee - storage
        return NetRealization(
            gross_amount=round(gross, 0),
            transport_cost=round(transport, 0),
            market_fee=round(market_fee, 0),
            storage_cost=round(storage, 0),
            net_amount=round(net, 0),
        )

    def _calculate_real_net_from_db(self, crop: str, quantity: float) -> NetRealization:
        """Calculate net realization using current DB prices."""
        from src.database import SessionLocal
        from src.repositories import get_latest_price
        db = SessionLocal()
        try:
            record = get_latest_price(db, crop)
            if record:
                return self._calculate_real_net(record.price, quantity)
            return self._dummy_net_realization(quantity)
        finally:
            db.close()

    # ── Agent interface (called by Supervisor) ───────────────────────────

    def handle_query(self, query: str, farmer_id: str, **ctx) -> AgentResponse:
        query_lower = query.lower()

        # Extract crop name from query or context
        crop = ctx.get("crop", self._extract_crop(query_lower))
        mandi = ctx.get("mandi", None)

        # Sell-or-store decision
        if any(w in query_lower for w in ["sell", "store", "wait", "bechna", "बेचना", "रुको", "बेचूं"]):
            decision = self.recommend_decision(farmer_id, crop)
            action_map = {
                "sell_now": "Sell immediately",
                "store_2_weeks": "Store for 2 weeks",
                "wait": "Wait for better prices",
            }
            resp_text = (
                f"Recommendation: {action_map.get(decision.recommendation, decision.recommendation)}. "
                f"Best mandi: {decision.best_mandi}. "
                f"Expected net realisation: ₹{decision.expected_net_realization:,.0f}. "
                f"Opportunity cost of waiting: ₹{decision.opportunity_cost:,.0f}. "
                f"Risk: {decision.risk_assessment}."
            )
            return AgentResponse(
                agent_name=self.NAME,
                response_text=resp_text,
                data=decision.model_dump(),
                confidence=0.78,
            )

        # Net realisation calculation
        if any(w in query_lower for w in ["net", "cost", "realization", "income", "कमाई"]):
            qty = ctx.get("quantity", 20.0)
            nr = self.calculate_net_realization(qty)
            resp_text = (
                f"For {qty} quintals: Gross ₹{nr.gross_amount:,.0f} — "
                f"Transport ₹{nr.transport_cost:,.0f}, Market fee ₹{nr.market_fee:,.0f}, "
                f"Storage ₹{nr.storage_cost:,.0f}. "
                f"Net income: ₹{nr.net_amount:,.0f}."
            )
            return AgentResponse(agent_name=self.NAME, response_text=resp_text, data=nr.model_dump(), confidence=0.85)

        # Default: price forecast
        forecast = self.forecast_price(crop, mandi)
        resp_text = (
            f"{forecast.crop.title()} at {forecast.mandi}: "
            f"₹{forecast.current_price:,.0f}/quintal (current). "
            f"7-day forecast: ₹{forecast.forecast_7day:,.0f}, "
            f"30-day forecast: ₹{forecast.forecast_30day:,.0f}. "
            f"Trend: {forecast.trend}. "
            f"Confidence band: ₹{forecast.confidence_lower:,.0f}-{forecast.confidence_upper:,.0f}."
        )
        return AgentResponse(
            agent_name=self.NAME,
            response_text=resp_text,
            data=forecast.model_dump(),
            confidence=0.8,
            has_chart=True,
            chart_url=f"https://cdn.krishimandal.com/charts/{crop}_price.png",
        )

    # ── Private helpers ──────────────────────────────────────────────────

    @staticmethod
    def _extract_crop(text: str) -> str:
        """Simple keyword-based crop extraction from query text."""
        crops = {
            "wheat": ["wheat", "gehun", "गेहूं"],
            "cotton": ["cotton", "kapas", "कपास"],
            "soybean": ["soybean", "soya", "soyabean", "सोयाबीन"],
            "sugarcane": ["sugarcane", "ganna", "गन्ना"],
            "onion": ["onion", "pyaz", "प्याज"],
            "rice": ["rice", "chawal", "चावल", "dhan", "धान"],
            "jowar": ["jowar", "ज्वार", "sorghum"],
            "bajra": ["bajra", "बाजरा", "millet"],
            "tur": ["tur", "toor", "arhar", "तूर", "अरहर"],
            "gram": ["gram", "chana", "चना"],
        }
        for crop_name, keywords in crops.items():
            if any(k in text for k in keywords):
                return crop_name
        return "wheat"  # default fallback

    def _fetch_enam_and_forecast(self, crop: str, mandi: str | None) -> PriceForecast:
        """Fetch real price data using the price fetcher chain, then forecast."""
        try:
            from src.data_fetchers.mandi_prices import get_price_fetcher
            fetcher = get_price_fetcher()
            entries = fetcher.fetch_prices([crop], state="Maharashtra", days_back=7)
            if entries:
                current = entries[0].price
                avg = sum(e.price for e in entries) / len(entries)
                prices = [e.price for e in entries]
                target_mandi = mandi or entries[0].mandi

                trend = "rising" if avg > current * 1.02 else ("falling" if avg < current * 0.98 else "stable")
                return PriceForecast(
                    crop=crop,
                    mandi=target_mandi,
                    current_price=round(current, 0),
                    forecast_7day=round(avg, 0),
                    forecast_30day=round(avg * 1.02, 0),
                    confidence_lower=round(min(prices) * 0.95, 0),
                    confidence_upper=round(max(prices) * 1.05, 0),
                    trend=trend,
                    factors=[{"factor": "real_market_data", "impact": 0.0, "explanation": "Based on live mandi prices"}],
                )
        except Exception as e:
            logger.warning("Real price fetch failed: %s", e)
        return self._forecast_from_db(crop, mandi)
