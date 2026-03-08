"""
KrishiMandal — Shared data models used across all agents.
Uses Pydantic v2 for validation and serialization.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────────

class GrowthStage(str, Enum):
    GERMINATION = "germination"
    VEGETATIVE = "vegetative"
    FLOWERING = "flowering"
    MATURITY = "maturity"
    HARVESTED = "harvested"


class SoilType(str, Enum):
    BLACK = "black"
    RED = "red"
    ALLUVIAL = "alluvial"
    LATERITE = "laterite"
    SANDY = "sandy"


class IrrigationType(str, Enum):
    RAINFED = "rainfed"
    CANAL = "canal"
    BOREWELL = "borewell"
    DRIP = "drip"
    SPRINKLER = "sprinkler"


class QualityGrade(str, Enum):
    A = "A"
    B = "B"
    C = "C"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ── Geo primitives ───────────────────────────────────────────────────────────

class GeoCoordinates(BaseModel):
    lat: float
    lng: float


# ── Farm models ──────────────────────────────────────────────────────────────

class CropInstance(BaseModel):
    crop_type: str
    variety: str = ""
    planting_date: date
    expected_harvest: Optional[date] = None
    area_hectares: float
    growth_stage: GrowthStage = GrowthStage.GERMINATION
    health_score: float = 80.0


class FarmProfile(BaseModel):
    farm_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    farmer_id: str
    farmer_name: str = ""
    phone: str = ""
    preferred_language: str = "hi-IN"
    location: GeoCoordinates
    area_hectares: float
    soil_type: SoilType = SoilType.BLACK
    irrigation_type: IrrigationType = IrrigationType.RAINFED
    current_crops: List[CropInstance] = []
    historical_crops: List[Dict[str, Any]] = []


class WeatherSnapshot(BaseModel):
    temperature_c: float
    humidity_pct: float
    rainfall_mm: float
    wind_speed_kmh: float
    condition: str = "clear"
    forecast_7day: List[Dict[str, Any]] = []


class FarmState(BaseModel):
    farm_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ndvi_mean: float = 0.65
    soil_moisture_pct: float = 45.0
    weather: Optional[WeatherSnapshot] = None
    health_score: float = 80.0


# ── Price models ─────────────────────────────────────────────────────────────

class PriceForecast(BaseModel):
    crop: str
    mandi: str
    current_price: float
    forecast_7day: float
    forecast_30day: float
    confidence_lower: float
    confidence_upper: float
    trend: str  # rising | falling | stable
    factors: List[Dict[str, Any]] = []


class MarketDecision(BaseModel):
    recommendation: str  # sell_now | store_N_weeks | wait
    expected_net_realization: float
    best_mandi: str
    timing: str
    risk_assessment: str
    opportunity_cost: float


class NetRealization(BaseModel):
    gross_amount: float
    transport_cost: float
    market_fee: float
    storage_cost: float
    net_amount: float


# ── Scheme & Credit models ───────────────────────────────────────────────────

class SchemeMatch(BaseModel):
    scheme_id: str
    scheme_name: str
    eligibility_score: float
    benefits_inr: float
    deadline: Optional[date] = None
    requirements: List[str] = []
    missing_criteria: List[str] = []
    application_url: str = ""


class CreditScore(BaseModel):
    farmer_id: str
    score: float
    components: Dict[str, float] = {}
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class LenderMatch(BaseModel):
    lender_name: str
    interest_rate: float
    max_amount: float
    tenure_months: int
    collateral_required: bool


# ── Crop Health models ───────────────────────────────────────────────────────

class HealthComponents(BaseModel):
    soil_score: int = 0
    season_score: int = 0
    stage_score: int = 0
    weather_score: int = 0


class CropHealth(BaseModel):
    farm_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    health_score: float
    ndvi_mean: float = 0.65
    components: HealthComponents = HealthComponents()
    anomalies: List[Dict[str, Any]] = []


class PestAlert(BaseModel):
    pest_type: str
    risk_level: float
    forecast_days: int
    recommended_actions: List[str]
    severity: AlertSeverity = AlertSeverity.MEDIUM


class InputRecommendation(BaseModel):
    input_type: str  # fertilizer | pesticide | irrigation
    product: str
    quantity_kg_per_hectare: float
    timing: str
    application_method: str
    expected_benefit: str
    cost_inr: float


# ── Supply Chain models ──────────────────────────────────────────────────────

class HarvestPlan(BaseModel):
    farm_id: str
    harvest_date: date
    expected_yield_quintals: float
    quality_grade: QualityGrade = QualityGrade.B
    labor_required: int
    target_markets: List[str] = []
    storage_recommendation: str = ""
    recommendations: List[str] = []


class MarketOption(BaseModel):
    mandi_name: str
    distance_km: float
    expected_price: float
    market_fee_pct: float
    net_realization: float
    payment_reliability: str


# ── Learning models ──────────────────────────────────────────────────────────

class LearningContent(BaseModel):
    content_id: str
    title: str
    content_type: str  # video | audio | text
    language: str
    topic: str
    url: str = ""
    duration_minutes: int = 0
    relevance_score: float = 0.0


# ── Orchestrator models ─────────────────────────────────────────────────────

class AgentResponse(BaseModel):
    agent_name: str
    response_text: str
    data: Dict[str, Any] = {}
    confidence: float = 0.85
    citations: List[str] = []
    has_chart: bool = False
    chart_url: str = ""
    has_actions: bool = False
    actions: List[Dict[str, str]] = []


class OrchestratorResult(BaseModel):
    query: str
    farmer_id: str
    language: str
    agents_invoked: List[str]
    final_response: str
    agent_responses: List[AgentResponse] = []
    processing_time_ms: int = 0


# ── CRUD Request / Response models ──────────────────────────────────────────

class CreateFarmRequest(BaseModel):
    farmer_id: str
    farmer_name: str
    phone: str
    preferred_language: str = "hi-IN"
    location_lat: float = 19.076
    location_lng: float = 72.877
    area_hectares: float
    soil_type: str = "black"
    irrigation_type: str = "rainfed"


class UpdateFarmRequest(BaseModel):
    farmer_name: Optional[str] = None
    phone: Optional[str] = None
    preferred_language: Optional[str] = None
    area_hectares: Optional[float] = None
    soil_type: Optional[str] = None
    irrigation_type: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None


class AddCropRequest(BaseModel):
    crop_type: str
    area_hectares: float
    variety: str = ""
    planting_date: Optional[date] = None
    expected_harvest: Optional[date] = None
    growth_stage: str = "germination"


class SimulateRequest(BaseModel):
    scenario: str = "drought"  # drought | pest_outbreak | early_harvest | alternative_crop


class PriceHistoryItem(BaseModel):
    crop: str
    mandi: str
    price: float
    date: str


class ErrorResponse(BaseModel):
    detail: str
    request_id: Optional[str] = None


# ── Application Models ─────────────────────────────────────────────────────

class ApplicationStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class DocumentChecklistItem(BaseModel):
    name: str
    uploaded: bool = False
    file_path: str = ""


class CreateApplicationRequest(BaseModel):
    scheme_id: str
    submit_directly: bool = False
    farmer_notes: str = ""


class UpdateApplicationRequest(BaseModel):
    action: str = "submit"  # submit | update
    farmer_notes: Optional[str] = None
    documents_checklist: Optional[List[DocumentChecklistItem]] = None


class ApplicationResponse(BaseModel):
    id: int
    farmer_id: str
    scheme_id: str
    scheme_name: str
    status: str
    applied_at: Optional[str] = None
    submitted_at: Optional[str] = None
    reviewed_at: Optional[str] = None
    updated_at: Optional[str] = None
    documents_checklist: List[DocumentChecklistItem] = []
    estimated_subsidy_inr: float = 0.0
    farmer_notes: str = ""
    reviewer_notes: str = ""


# ── Inventory Models ───────────────────────────────────────────────────────

class CreateInventoryRequest(BaseModel):
    name: str
    category: str  # seed|fertilizer|pesticide|harvest|equipment
    quantity: float = 0.0
    unit: str = "kg"
    alert_threshold: float = 0.0
    purchase_price: float = 0.0
    purchase_date: Optional[date] = None
    expiry_date: Optional[date] = None
    notes: str = ""


class UpdateInventoryRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    alert_threshold: Optional[float] = None
    purchase_price: Optional[float] = None
    purchase_date: Optional[date] = None
    expiry_date: Optional[date] = None
    notes: Optional[str] = None


class AdjustStockRequest(BaseModel):
    adjustment: float
    reason: str = ""


class InventoryItemResponse(BaseModel):
    id: int
    farmer_id: str
    name: str
    category: str
    quantity: float
    unit: str
    alert_threshold: float
    purchase_price: float
    purchase_date: Optional[str] = None
    expiry_date: Optional[str] = None
    notes: str
    is_low_stock: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ── Notification Models ────────────────────────────────────────────────────

class NotificationType(str, Enum):
    SCHEME_DEADLINE = "scheme_deadline"
    PRICE_ALERT = "price_alert"
    PEST_WARNING = "pest_warning"
    APPLICATION_UPDATE = "application_update"
    INVENTORY_ALERT = "inventory_alert"
    WEATHER_ALERT = "weather_alert"
    GENERAL = "general"


class NotificationResponse(BaseModel):
    id: int
    farmer_id: str
    type: str
    title: str
    message: str
    channel: str
    is_read: bool
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    created_at: Optional[str] = None
    read_at: Optional[str] = None
