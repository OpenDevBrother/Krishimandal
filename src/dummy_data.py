"""
KrishiMandal — Dummy / mock data generators.
All agents import from here when settings.USE_DUMMY_DATA is True,
so the system works end-to-end without real API keys.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from src.models import (
    AlertSeverity,
    CreditScore,
    CropHealth,
    CropInstance,
    FarmProfile,
    FarmState,
    GeoCoordinates,
    GrowthStage,
    HarvestPlan,
    HealthComponents,
    InputRecommendation,
    IrrigationType,
    LearningContent,
    LenderMatch,
    MarketDecision,
    MarketOption,
    NetRealization,
    PestAlert,
    PriceForecast,
    QualityGrade,
    SchemeMatch,
    SoilType,
    WeatherSnapshot,
)

# ── Constants ────────────────────────────────────────────────────────────────

MAHARASHTRA_CROPS = ["wheat", "cotton", "soybean", "sugarcane", "jowar", "bajra", "tur", "gram", "onion", "grapes"]
MAHARASHTRA_MANDIS = [
    "Pune (Gultekdi)", "Nashik", "Nagpur (Kalamna)", "Aurangabad",
    "Solapur", "Kolhapur", "Sangli", "Ahmednagar", "Latur", "Jalgaon",
]
SCHEMES = [
    {"id": "PMKISAN", "name": "PM-KISAN Samman Nidhi", "benefits": 6000, "url": "https://pmkisan.gov.in"},
    {"id": "PMFBY", "name": "PM Fasal Bima Yojana", "benefits": 25000, "url": "https://pmfby.gov.in"},
    {"id": "PMKUSUM", "name": "PM-KUSUM Solar Pump", "benefits": 50000, "url": "https://mnre.gov.in/pmkusum"},
    {"id": "SHC", "name": "Soil Health Card Scheme", "benefits": 0, "url": "https://soilhealth.dac.gov.in"},
    {"id": "KCC", "name": "Kisan Credit Card", "benefits": 300000, "url": "https://www.nabard.org"},
    {"id": "MKSP", "name": "Mahila Kisan Sashaktikaran Pariyojana", "benefits": 15000, "url": "https://nrlm.gov.in"},
    {"id": "NMSA", "name": "National Mission for Sustainable Agriculture", "benefits": 20000, "url": "https://nmsa.dac.gov.in"},
    {"id": "RKVY", "name": "Rashtriya Krishi Vikas Yojana", "benefits": 10000, "url": "https://rkvy.nic.in"},
    {"id": "BKSY", "name": "Bhagyalaxmi Krishi Sinchan Yojana (MH)", "benefits": 30000, "url": "https://mahadbt.maharashtra.gov.in"},
    {"id": "SJSY", "name": "Shetkari Jansuraksha Yojana (MH)", "benefits": 200000, "url": "https://mahadbt.maharashtra.gov.in"},
]
LEARNING_TOPICS = [
    "pest-control", "organic-farming", "drip-irrigation", "soil-health",
    "market-linkage", "post-harvest", "seed-selection", "water-management",
]


# ── Farm data ────────────────────────────────────────────────────────────────

def dummy_farm_profile(farmer_id: str = "F1001") -> FarmProfile:
    crop = random.choice(MAHARASHTRA_CROPS[:5])
    return FarmProfile(
        farm_id="FARM-" + farmer_id,
        farmer_id=farmer_id,
        farmer_name="Rajesh Patil",
        phone="+919876543210",
        preferred_language="hi-IN",
        location=GeoCoordinates(lat=19.076, lng=72.877),
        area_hectares=round(random.uniform(0.5, 4.0), 1),
        soil_type=random.choice(list(SoilType)),
        irrigation_type=random.choice(list(IrrigationType)),
        current_crops=[
            CropInstance(
                crop_type=crop,
                variety=f"{crop.title()} HD-2967",
                planting_date=date.today() - timedelta(days=random.randint(40, 100)),
                expected_harvest=date.today() + timedelta(days=random.randint(20, 60)),
                area_hectares=round(random.uniform(0.5, 3.0), 1),
                growth_stage=random.choice([GrowthStage.VEGETATIVE, GrowthStage.FLOWERING, GrowthStage.MATURITY]),
                health_score=round(random.uniform(60, 95), 1),
            )
        ],
        historical_crops=[
            {"season": "Kharif 2025", "crop": "soybean", "yield_quintals": 12.5},
            {"season": "Rabi 2024-25", "crop": "wheat", "yield_quintals": 18.0},
            {"season": "Kharif 2024", "crop": "cotton", "yield_quintals": 8.3},
        ],
    )


def dummy_farm_state(farm_id: str = "FARM-F1001") -> FarmState:
    return FarmState(
        farm_id=farm_id,
        ndvi_mean=round(random.uniform(0.45, 0.82), 2),
        soil_moisture_pct=round(random.uniform(25, 65), 1),
        weather=dummy_weather(),
        health_score=round(random.uniform(60, 95), 1),
    )


def dummy_weather() -> WeatherSnapshot:
    return WeatherSnapshot(
        temperature_c=round(random.uniform(18, 38), 1),
        humidity_pct=round(random.uniform(30, 80), 1),
        rainfall_mm=round(random.uniform(0, 15), 1),
        wind_speed_kmh=round(random.uniform(5, 25), 1),
        condition=random.choice(["clear", "partly_cloudy", "cloudy", "light_rain"]),
        forecast_7day=[
            {
                "date": (date.today() + timedelta(days=i)).isoformat(),
                "temp_high": round(random.uniform(28, 40), 1),
                "temp_low": round(random.uniform(15, 25), 1),
                "rain_mm": round(random.uniform(0, 20), 1),
                "condition": random.choice(["clear", "cloudy", "rain"]),
            }
            for i in range(1, 8)
        ],
    )


# ── Price data ───────────────────────────────────────────────────────────────

def dummy_price_forecast(crop: str = "wheat", mandi: str | None = None) -> PriceForecast:
    mandi = mandi or random.choice(MAHARASHTRA_MANDIS)
    base = random.uniform(1800, 3500)
    return PriceForecast(
        crop=crop,
        mandi=mandi,
        current_price=round(base, 0),
        forecast_7day=round(base * random.uniform(0.97, 1.08), 0),
        forecast_30day=round(base * random.uniform(0.92, 1.15), 0),
        confidence_lower=round(base * 0.9, 0),
        confidence_upper=round(base * 1.12, 0),
        trend=random.choice(["rising", "falling", "stable"]),
        factors=[
            {"factor": "supply", "impact": round(random.uniform(-0.5, 0.5), 2), "explanation": "Regional harvest arrivals are moderate"},
            {"factor": "demand", "impact": round(random.uniform(0, 0.4), 2), "explanation": "Festival season driving demand"},
            {"factor": "weather", "impact": round(random.uniform(-0.3, 0.1), 2), "explanation": "Unseasonal rains affecting quality"},
        ],
    )


def dummy_market_decision(farm_id: str, crop: str = "wheat") -> MarketDecision:
    return MarketDecision(
        recommendation=random.choice(["sell_now", "store_2_weeks", "wait"]),
        expected_net_realization=round(random.uniform(25000, 80000), 0),
        best_mandi=random.choice(MAHARASHTRA_MANDIS),
        timing=(date.today() + timedelta(days=random.randint(0, 14))).isoformat(),
        risk_assessment=random.choice(["low", "moderate", "high"]),
        opportunity_cost=round(random.uniform(500, 5000), 0),
    )


def dummy_net_realization(quantity_quintals: float = 20.0) -> NetRealization:
    price = random.uniform(2000, 3500)
    gross = price * quantity_quintals
    transport = random.uniform(500, 2500)
    fee = gross * 0.015
    storage = random.uniform(0, 1500)
    return NetRealization(
        gross_amount=round(gross, 0),
        transport_cost=round(transport, 0),
        market_fee=round(fee, 0),
        storage_cost=round(storage, 0),
        net_amount=round(gross - transport - fee - storage, 0),
    )


# ── Scheme & Credit data ────────────────────────────────────────────────────

def dummy_scheme_matches(farmer_profile: FarmProfile | None = None) -> List[SchemeMatch]:
    matches = []
    for s in SCHEMES:
        matches.append(
            SchemeMatch(
                scheme_id=s["id"],
                scheme_name=s["name"],
                eligibility_score=round(random.uniform(0.6, 1.0), 2),
                benefits_inr=s["benefits"],
                deadline=date.today() + timedelta(days=random.randint(10, 90)),
                requirements=["Aadhaar", "Land Record", "Bank Passbook"],
                missing_criteria=random.choice([[], ["Income Certificate"], ["Caste Certificate"]]),
                application_url=s["url"],
            )
        )
    return matches


def dummy_credit_score(farmer_id: str = "F1001") -> CreditScore:
    return CreditScore(
        farmer_id=farmer_id,
        score=round(random.uniform(55, 92), 1),
        components={
            "farm_activity": round(random.uniform(15, 28), 1),
            "crop_health": round(random.uniform(12, 24), 1),
            "market_engagement": round(random.uniform(8, 18), 1),
            "peer_reputation": round(random.uniform(5, 14), 1),
            "scheme_compliance": round(random.uniform(3, 9), 1),
        },
    )


def dummy_lender_matches() -> List[LenderMatch]:
    return [
        LenderMatch(lender_name="SBI Kisan Card", interest_rate=7.0, max_amount=300000, tenure_months=12, collateral_required=False),
        LenderMatch(lender_name="NABARD MFI Partner", interest_rate=9.5, max_amount=100000, tenure_months=6, collateral_required=False),
        LenderMatch(lender_name="HDFC Kisan Gold", interest_rate=8.5, max_amount=500000, tenure_months=24, collateral_required=True),
    ]


# ── Crop Health data ────────────────────────────────────────────────────────

def dummy_crop_health(farm_id: str = "FARM-F1001") -> CropHealth:
    soil = random.randint(14, 24)
    season = random.randint(14, 24)
    stage = random.randint(14, 24)
    weather = random.randint(14, 24)
    return CropHealth(
        farm_id=farm_id,
        health_score=soil + season + stage + weather,
        ndvi_mean=round(random.uniform(0.45, 0.82), 2),
        components=HealthComponents(soil_score=soil, season_score=season, stage_score=stage, weather_score=weather),
        anomalies=[
            {"location": {"lat": 19.076, "lng": 72.877}, "type": "water_stress", "severity": 0.3, "confidence": 0.7},
        ] if random.random() > 0.5 else [],
    )


def dummy_pest_alerts(crop: str = "wheat") -> List[PestAlert]:
    pests = {
        "wheat": [("aphid", "Apply neem-based spray"), ("rust", "Use fungicide Propiconazole")],
        "cotton": [("bollworm", "Install pheromone traps"), ("whitefly", "Apply yellow sticky traps")],
        "soybean": [("pod_borer", "Spray Novaluron 10 EC"), ("leaf_miner", "Apply Profenofos")],
    }
    pest_list = pests.get(crop, pests["wheat"])
    alerts = []
    for p_name, action in pest_list:
        if random.random() > 0.4:
            alerts.append(
                PestAlert(
                    pest_type=p_name,
                    risk_level=round(random.uniform(0.3, 0.9), 2),
                    forecast_days=random.randint(3, 7),
                    recommended_actions=[action, "Monitor field edges daily"],
                    severity=random.choice([AlertSeverity.LOW, AlertSeverity.MEDIUM, AlertSeverity.HIGH]),
                )
            )
    return alerts or [PestAlert(pest_type="none", risk_level=0.05, forecast_days=7, recommended_actions=["No action needed"])]


def dummy_input_recommendation(crop: str = "wheat") -> List[InputRecommendation]:
    return [
        InputRecommendation(
            input_type="fertilizer",
            product="DAP (Di-Ammonium Phosphate)",
            quantity_kg_per_hectare=50,
            timing="At sowing or first irrigation",
            application_method="Broadcasting",
            expected_benefit="Improved root development and early vigour",
            cost_inr=1350,
        ),
        InputRecommendation(
            input_type="irrigation",
            product="Scheduled irrigation",
            quantity_kg_per_hectare=0,
            timing="Every 15 days during vegetative stage",
            application_method="Flood or drip",
            expected_benefit="Optimal soil moisture for growth",
            cost_inr=0,
        ),
    ]


# ── Supply Chain data ───────────────────────────────────────────────────────

def dummy_harvest_plan(farm_id: str = "FARM-F1001", crop: str = "wheat") -> HarvestPlan:
    return HarvestPlan(
        farm_id=farm_id,
        harvest_date=date.today() + timedelta(days=random.randint(7, 30)),
        expected_yield_quintals=round(random.uniform(8, 30), 1),
        quality_grade=random.choice([QualityGrade.A, QualityGrade.B]),
        labor_required=random.randint(3, 10),
        target_markets=random.sample(MAHARASHTRA_MANDIS, k=3),
        storage_recommendation=random.choice([
            "Sell immediately — prices are favourable.",
            "Store for 2 weeks in Solapur cold storage (₹15/qtl/day).",
            "Consider FPO pooling with nearby farmers for better rate.",
        ]),
        recommendations=[
            "Arrange combine harvester 3 days before harvest.",
            "Ensure gunny bags are clean and dry.",
            "Get quality grading done at nearest APMC.",
        ],
    )


def dummy_market_options(crop: str = "wheat") -> List[MarketOption]:
    options = []
    for mandi in random.sample(MAHARASHTRA_MANDIS, k=4):
        price = random.uniform(2000, 3500)
        fee = 1.5
        dist = random.uniform(10, 80)
        transport = dist * 3.5
        net = price * 20 - transport - (price * 20 * fee / 100)
        options.append(
            MarketOption(
                mandi_name=mandi,
                distance_km=round(dist, 1),
                expected_price=round(price, 0),
                market_fee_pct=fee,
                net_realization=round(net, 0),
                payment_reliability=random.choice(["excellent", "good", "average"]),
            )
        )
    return sorted(options, key=lambda x: x.net_realization, reverse=True)


# ── Learning data ───────────────────────────────────────────────────────────

def dummy_learning_content(topic: str | None = None, language: str = "hi-IN") -> List[LearningContent]:
    topic = topic or random.choice(LEARNING_TOPICS)
    contents = [
        LearningContent(
            content_id=f"LC-{random.randint(1000,9999)}",
            title=f"{topic.replace('-', ' ').title()} — Best Practices",
            content_type="video",
            language=language,
            topic=topic,
            url=f"https://cdn.krishimandal.com/learning/{topic}/video_01.mp4",
            duration_minutes=random.randint(5, 15),
            relevance_score=round(random.uniform(0.7, 0.98), 2),
        ),
        LearningContent(
            content_id=f"LC-{random.randint(1000,9999)}",
            title=f"ICAR Bulletin: {topic.replace('-', ' ').title()}",
            content_type="text",
            language=language,
            topic=topic,
            url=f"https://cdn.krishimandal.com/learning/{topic}/icar_bulletin.pdf",
            duration_minutes=10,
            relevance_score=round(random.uniform(0.6, 0.9), 2),
        ),
        LearningContent(
            content_id=f"LC-{random.randint(1000,9999)}",
            title=f"Audio Guide: {topic.replace('-', ' ').title()}",
            content_type="audio",
            language=language,
            topic=topic,
            url=f"https://cdn.krishimandal.com/learning/{topic}/audio_guide.mp3",
            duration_minutes=random.randint(3, 8),
            relevance_score=round(random.uniform(0.65, 0.88), 2),
        ),
    ]
    return contents
