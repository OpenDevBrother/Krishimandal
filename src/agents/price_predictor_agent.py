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
        return self._fetch_enam_and_forecast(crop, mandi)

    def recommend_decision(self, farmer_id: str, crop: str, quantity_quintals: float = 20.0) -> MarketDecision:
        """Sell now / store / wait recommendation."""
        if settings.USE_DUMMY_DATA:
            return self._dummy_market_decision(farmer_id, crop)
        return self._dummy_market_decision(farmer_id, crop)

    def calculate_net_realization(self, quantity_quintals: float = 20.0) -> NetRealization:
        """Compute net income after transport, fees, and storage."""
        if settings.USE_DUMMY_DATA:
            return self._dummy_net_realization(quantity_quintals)
        return self._dummy_net_realization(quantity_quintals)

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
        """Attempt to fetch real price data from e-NAM and produce a forecast.
        Falls back to dummy data on failure.
        """
        try:
            import requests
            # e-NAM doesn't have a stable public JSON API; this is illustrative.
            # In production, scrape or use government data.gov.in datasets.
            logger.info(f"Fetching e-NAM data for {crop}")
            # ... (real implementation would go here)
            raise NotImplementedError("e-NAM scraper not yet implemented")
        except Exception as e:
            logger.warning(f"e-NAM fetch failed, using dummy data: {e}")
            return self._dummy_price_forecast(crop, mandi)
