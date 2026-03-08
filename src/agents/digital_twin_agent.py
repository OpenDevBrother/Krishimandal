"""
KrishiMandal — Digital Twin Agent
Maintains a virtual replica of the farmer's land, simulates scenarios,
predicts yields and harvest windows.

NOTE: Per user instruction, we do NOT build the full Digital Twin software.
This agent acts as the agentic interface that retrieves / generates farm
state information for other agents to consume.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, Optional

from src.config import settings
from src.models import (
    AgentResponse,
    CropInstance,
    FarmProfile,
    FarmState,
    GeoCoordinates,
    GrowthStage,
    WeatherSnapshot,
)

logger = logging.getLogger(__name__)


class DigitalTwinAgent:
    """Agent that manages farm profile and state information."""

    NAME = "digital_twin"

    def __init__(self):
        # In production this would connect to RDS, Redis, Satellite APIs, etc.
        from src.dummy_data import dummy_farm_profile, dummy_farm_state, dummy_weather
        self._dummy_farm_profile = dummy_farm_profile
        self._dummy_farm_state = dummy_farm_state
        self._dummy_weather = dummy_weather
        self._farm_store: Dict[str, FarmProfile] = {}

    # ── Public methods ───────────────────────────────────────────────────

    def get_farm_profile(self, farmer_id: str) -> FarmProfile:
        """Retrieve or create a farm profile for the given farmer."""
        if farmer_id in self._farm_store:
            return self._farm_store[farmer_id]
        profile = self._dummy_farm_profile(farmer_id)
        self._farm_store[farmer_id] = profile
        return profile

    def get_farm_state(self, farm_id: str) -> FarmState:
        """Get the current state snapshot of a farm (NDVI, moisture, weather)."""
        if settings.USE_DUMMY_DATA:
            return self._dummy_farm_state(farm_id)
        # Production: pull from Redis cache → RDS → Satellite API
        return self._dummy_farm_state(farm_id)

    def get_weather(self, location: GeoCoordinates) -> WeatherSnapshot:
        """Fetch current weather + 7-day forecast for a location."""
        if settings.USE_DUMMY_DATA:
            return self._dummy_weather()
        return self._fetch_weather_api(location)

    def predict_harvest(self, farmer_id: str) -> Dict[str, Any]:
        """Predict harvest window based on growth stage and weather."""
        profile = self.get_farm_profile(farmer_id)
        if not profile.current_crops:
            return {"message": "No active crops found."}

        crop = profile.current_crops[0]
        days_since_planting = (date.today() - crop.planting_date).days
        # Simplified harvest prediction
        days_to_harvest = max(10, 120 - days_since_planting)  # Typical 120-day crop
        predicted_date = date.today() + timedelta(days=days_to_harvest)

        return {
            "crop": crop.crop_type,
            "variety": crop.variety,
            "growth_stage": crop.growth_stage.value,
            "days_since_planting": days_since_planting,
            "predicted_harvest_date": predicted_date.isoformat(),
            "days_to_harvest": days_to_harvest,
            "confidence": 0.78,
            "yield_estimate_quintals_per_hectare": round(18 + (crop.health_score - 70) * 0.3, 1),
        }

    def simulate_scenario(self, farmer_id: str, scenario: str) -> Dict[str, Any]:
        """Run a simple what-if simulation for the farmer's crop."""
        profile = self.get_farm_profile(farmer_id)
        crop = profile.current_crops[0] if profile.current_crops else None

        scenarios = {
            "drought": {
                "scenario": "No rainfall for next 3 weeks",
                "yield_impact_pct": -25,
                "recommendation": "Arrange supplementary irrigation immediately. Consider drip irrigation to conserve water.",
                "risk": "high",
            },
            "pest_outbreak": {
                "scenario": "Pest infestation on 30% of the field",
                "yield_impact_pct": -15,
                "recommendation": "Apply targeted neem-based spray. Monitor field edges. Consider bio-control agents.",
                "risk": "medium",
            },
            "early_harvest": {
                "scenario": "Harvest 10 days earlier than predicted",
                "yield_impact_pct": -8,
                "recommendation": "Yield may be slightly lower but prices could be better. Check mandi trends.",
                "risk": "low",
            },
            "alternative_crop": {
                "scenario": f"Switch from {crop.crop_type if crop else 'current crop'} to soybean next season",
                "yield_impact_pct": 0,
                "recommendation": "Soybean is well-suited for your soil type. Expected income: ₹35,000-45,000/hectare.",
                "risk": "low",
            },
        }

        result = scenarios.get(scenario, scenarios["drought"])
        result["farm_id"] = profile.farm_id
        result["current_crop"] = crop.crop_type if crop else "none"
        return result

    def generate_risk_alerts(self, farmer_id: str) -> list:
        """Check farm conditions and generate relevant alerts."""
        state = self.get_farm_state(f"FARM-{farmer_id}")
        alerts = []

        if state.soil_moisture_pct < 30:
            alerts.append({
                "type": "drought_risk",
                "severity": "high",
                "message": f"Soil moisture critically low at {state.soil_moisture_pct}%. Irrigate within 48 hours.",
            })

        if state.weather and state.weather.temperature_c > 40:
            alerts.append({
                "type": "heat_stress",
                "severity": "medium",
                "message": f"Temperature at {state.weather.temperature_c}°C. Consider mulching to protect crops.",
            })

        if state.ndvi_mean < 0.4:
            alerts.append({
                "type": "crop_health_decline",
                "severity": "high",
                "message": f"NDVI dropped to {state.ndvi_mean}. Inspect field for pest/disease.",
            })

        if not alerts:
            alerts.append({
                "type": "all_clear",
                "severity": "low",
                "message": "Farm conditions are healthy. No immediate action required.",
            })

        return alerts

    # ── Agent interface (called by Supervisor) ───────────────────────────

    def handle_query(self, query: str, farmer_id: str, **ctx) -> AgentResponse:
        """Main entry point called by the Supervisor agent."""
        query_lower = query.lower()

        if any(w in query_lower for w in ["harvest", "katai", "काटना"]):
            data = self.predict_harvest(farmer_id)
            resp = (
                f"Your {data.get('crop', 'crop')} is in the {data.get('growth_stage', '')} stage. "
                f"Predicted harvest date: {data.get('predicted_harvest_date', 'N/A')} "
                f"(about {data.get('days_to_harvest', '?')} days). "
                f"Expected yield: {data.get('yield_estimate_quintals_per_hectare', '?')} quintals/hectare."
            )
            return AgentResponse(agent_name=self.NAME, response_text=resp, data=data, confidence=0.82)

        if any(w in query_lower for w in ["weather", "mausam", "barish", "बारिश", "मौसम"]):
            profile = self.get_farm_profile(farmer_id)
            weather = self.get_weather(profile.location)
            resp = (
                f"Current weather: {weather.condition}, {weather.temperature_c}°C, "
                f"humidity {weather.humidity_pct}%, rainfall {weather.rainfall_mm}mm. "
                f"Wind: {weather.wind_speed_kmh} km/h."
            )
            return AgentResponse(agent_name=self.NAME, response_text=resp, data=weather.model_dump(), confidence=0.9)

        if any(w in query_lower for w in ["scenario", "simulate", "what if", "अगर"]):
            scenario_type = "drought"
            for s in ["drought", "pest", "early_harvest", "alternative_crop"]:
                if s.replace("_", " ") in query_lower:
                    scenario_type = s
                    break
            data = self.simulate_scenario(farmer_id, scenario_type)
            resp = (
                f"Scenario: {data['scenario']}. "
                f"Impact on yield: {data['yield_impact_pct']}%. "
                f"Recommendation: {data['recommendation']}"
            )
            return AgentResponse(agent_name=self.NAME, response_text=resp, data=data, confidence=0.75)

        if any(w in query_lower for w in ["alert", "risk", "danger", "खतरा", "चेतावनी"]):
            alerts = self.generate_risk_alerts(farmer_id)
            resp = " | ".join(a["message"] for a in alerts)
            return AgentResponse(agent_name=self.NAME, response_text=resp, data={"alerts": alerts}, confidence=0.85)

        # Default: return farm status overview
        profile = self.get_farm_profile(farmer_id)
        state = self.get_farm_state(profile.farm_id)
        crop = profile.current_crops[0] if profile.current_crops else None
        resp = (
            f"Farm overview for {profile.farmer_name}: "
            f"{profile.area_hectares} hectares, {profile.soil_type.value} soil, "
            f"{profile.irrigation_type.value} irrigation. "
            f"Current crop: {crop.crop_type if crop else 'none'} ({crop.growth_stage.value if crop else 'N/A'}). "
            f"Health score: {state.health_score}/100, NDVI: {state.ndvi_mean}."
        )
        return AgentResponse(agent_name=self.NAME, response_text=resp, data=profile.model_dump(mode="json"), confidence=0.88)

    # ── Private helpers ──────────────────────────────────────────────────

    def _fetch_weather_api(self, location: GeoCoordinates) -> WeatherSnapshot:
        """Call OpenWeatherMap API for real weather data."""
        import requests
        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                "lat": location.lat,
                "lon": location.lng,
                "appid": settings.OPENWEATHERMAP_API_KEY,
                "units": "metric",
            }
            r = requests.get(url, params=params, timeout=5)
            r.raise_for_status()
            d = r.json()
            return WeatherSnapshot(
                temperature_c=d["main"]["temp"],
                humidity_pct=d["main"]["humidity"],
                rainfall_mm=d.get("rain", {}).get("1h", 0),
                wind_speed_kmh=d["wind"]["speed"] * 3.6,
                condition=d["weather"][0]["main"].lower(),
            )
        except Exception as e:
            logger.warning(f"Weather API failed, using dummy data: {e}")
            return self._dummy_weather()
