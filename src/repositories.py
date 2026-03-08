"""
KrishiMandal — Repository layer for DB queries.
Keeps database logic out of agents.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from src.db_models import (
    CreditScoreRecord,
    Crop,
    Farm,
    Farmer,
    FarmStateRecord,
    InventoryItem,
    LearningProgress,
    Notification,
    PriceRecord,
    Scheme,
    SchemeApplication,
)
from src.models import (
    CreditScore,
    CropInstance,
    FarmProfile,
    FarmState,
    GeoCoordinates,
    GrowthStage,
    IrrigationType,
    SchemeMatch,
    SoilType,
    WeatherSnapshot,
)


# ── Farmer / Farm ────────────────────────────────────────────────────────────

def get_farmer(db: Session, farmer_id: str) -> Optional[Farmer]:
    return db.query(Farmer).filter(Farmer.id == farmer_id).first()


def create_farmer(db: Session, farmer_id: str, name: str, phone: str, language: str = "hi-IN") -> Farmer:
    farmer = Farmer(id=farmer_id, name=name, phone=phone, preferred_language=language)
    db.add(farmer)
    db.commit()
    db.refresh(farmer)
    return farmer


def get_farm(db: Session, farm_id: str) -> Optional[Farm]:
    return db.query(Farm).filter(Farm.id == farm_id).first()


def get_farm_by_farmer(db: Session, farmer_id: str) -> Optional[Farm]:
    return db.query(Farm).filter(Farm.farmer_id == farmer_id).first()


def create_farm(
    db: Session,
    farm_id: str,
    farmer_id: str,
    area_hectares: float,
    soil_type: str = "black",
    irrigation_type: str = "rainfed",
    lat: float = 19.076,
    lng: float = 72.877,
) -> Farm:
    farm = Farm(
        id=farm_id,
        farmer_id=farmer_id,
        area_hectares=area_hectares,
        soil_type=soil_type,
        irrigation_type=irrigation_type,
        location_lat=lat,
        location_lng=lng,
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


def update_farm(db: Session, farm: Farm, **kwargs) -> Farm:
    for key, value in kwargs.items():
        if hasattr(farm, key):
            setattr(farm, key, value)
    db.commit()
    db.refresh(farm)
    return farm


def delete_farmer(db: Session, farmer_id: str) -> bool:
    farmer = get_farmer(db, farmer_id)
    if not farmer:
        return False
    db.delete(farmer)
    db.commit()
    return True


def farm_to_profile(farm: Farm) -> FarmProfile:
    """Convert ORM Farm + related objects to Pydantic FarmProfile."""
    farmer = farm.farmer
    current_crops = [
        CropInstance(
            crop_type=c.crop_type,
            variety=c.variety,
            planting_date=c.planting_date,
            expected_harvest=c.expected_harvest,
            area_hectares=c.area_hectares,
            growth_stage=GrowthStage(c.growth_stage) if c.growth_stage in [e.value for e in GrowthStage] else GrowthStage.GERMINATION,
            health_score=c.health_score,
        )
        for c in farm.crops if c.is_current
    ]
    historical_crops = [
        {"season": c.season, "crop": c.crop_type, "yield_quintals": c.yield_quintals}
        for c in farm.crops if not c.is_current
    ]
    return FarmProfile(
        farm_id=farm.id,
        farmer_id=farmer.id,
        farmer_name=farmer.name,
        phone=farmer.phone,
        preferred_language=farmer.preferred_language,
        location=GeoCoordinates(lat=farm.location_lat, lng=farm.location_lng),
        area_hectares=farm.area_hectares,
        soil_type=SoilType(farm.soil_type) if farm.soil_type in [e.value for e in SoilType] else SoilType.BLACK,
        irrigation_type=IrrigationType(farm.irrigation_type) if farm.irrigation_type in [e.value for e in IrrigationType] else IrrigationType.RAINFED,
        current_crops=current_crops,
        historical_crops=historical_crops,
    )


# ── Crops ────────────────────────────────────────────────────────────────────

def add_crop(
    db: Session,
    farm_id: str,
    crop_type: str,
    area_hectares: float,
    variety: str = "",
    planting_date: Optional[date] = None,
    expected_harvest: Optional[date] = None,
    growth_stage: str = "germination",
) -> Crop:
    crop = Crop(
        farm_id=farm_id,
        crop_type=crop_type,
        variety=variety,
        planting_date=planting_date or date.today(),
        expected_harvest=expected_harvest,
        area_hectares=area_hectares,
        growth_stage=growth_stage,
        is_current=True,
    )
    db.add(crop)
    db.commit()
    db.refresh(crop)
    return crop


# ── Farm State ───────────────────────────────────────────────────────────────

def save_farm_state(db: Session, farm_id: str, ndvi: float, moisture: float, health: float, weather_dict: dict = None) -> FarmStateRecord:
    record = FarmStateRecord(
        farm_id=farm_id,
        ndvi_mean=ndvi,
        soil_moisture_pct=moisture,
        health_score=health,
        weather_json=json.dumps(weather_dict or {}),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_latest_farm_state(db: Session, farm_id: str) -> Optional[FarmStateRecord]:
    return (
        db.query(FarmStateRecord)
        .filter(FarmStateRecord.farm_id == farm_id)
        .order_by(FarmStateRecord.timestamp.desc())
        .first()
    )


def farm_state_to_pydantic(record: FarmStateRecord) -> FarmState:
    weather_data = json.loads(record.weather_json) if record.weather_json else None
    weather = WeatherSnapshot(**weather_data) if weather_data and weather_data.get("temperature_c") else None
    return FarmState(
        farm_id=record.farm_id,
        timestamp=record.timestamp,
        ndvi_mean=record.ndvi_mean,
        soil_moisture_pct=record.soil_moisture_pct,
        weather=weather,
        health_score=record.health_score,
    )


# ── Prices ───────────────────────────────────────────────────────────────────

def save_price(db: Session, crop: str, mandi: str, price: float) -> PriceRecord:
    record = PriceRecord(crop=crop, mandi=mandi, price=price)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_price_history(db: Session, crop: str, mandi: Optional[str] = None, days: int = 30) -> List[PriceRecord]:
    cutoff = datetime.utcnow() - timedelta(days=days)
    q = db.query(PriceRecord).filter(PriceRecord.crop == crop, PriceRecord.recorded_at >= cutoff)
    if mandi:
        q = q.filter(PriceRecord.mandi == mandi)
    return q.order_by(PriceRecord.recorded_at.desc()).all()


def get_latest_price(db: Session, crop: str, mandi: Optional[str] = None) -> Optional[PriceRecord]:
    q = db.query(PriceRecord).filter(PriceRecord.crop == crop)
    if mandi:
        q = q.filter(PriceRecord.mandi == mandi)
    return q.order_by(PriceRecord.recorded_at.desc()).first()


# ── Schemes ──────────────────────────────────────────────────────────────────

def get_all_schemes(db: Session, active_only: bool = True) -> List[Scheme]:
    q = db.query(Scheme)
    if active_only:
        q = q.filter(Scheme.is_active == True)  # noqa: E712
    return q.all()


def scheme_to_match(
    scheme: Scheme,
    farmer_profile: dict | None = None,
) -> SchemeMatch:
    """Convert Scheme ORM to SchemeMatch with real eligibility scoring."""
    requirements = json.loads(scheme.requirements_json) if scheme.requirements_json else []
    eligibility = json.loads(scheme.eligibility_json) if getattr(scheme, "eligibility_json", None) else {}

    eligibility_score = 0.85  # default
    missing_criteria: list[str] = []

    if farmer_profile and eligibility:
        score = 1.0
        # Check land size
        max_land = eligibility.get("land_size_max_ha")
        if max_land is not None and farmer_profile.get("land_size_ha", 0) > max_land:
            score -= 0.3
            missing_criteria.append(f"Land must be ≤{max_land} hectares")

        # Check income
        max_income = eligibility.get("income_max_inr")
        if max_income is not None and farmer_profile.get("income_inr", 0) > max_income:
            score -= 0.3
            missing_criteria.append(f"Income must be ≤₹{max_income:,.0f}")

        # Check state
        allowed_states = eligibility.get("states", [])
        if allowed_states and farmer_profile.get("state", "") not in allowed_states:
            score -= 0.4
            missing_criteria.append(f"Scheme available in: {', '.join(allowed_states)}")

        # Check age
        age_min = eligibility.get("age_min", 0)
        age_max = eligibility.get("age_max")
        farmer_age = farmer_profile.get("age", 30)
        if farmer_age < age_min:
            score -= 0.2
            missing_criteria.append(f"Minimum age: {age_min}")
        if age_max and farmer_age > age_max:
            score -= 0.2
            missing_criteria.append(f"Maximum age: {age_max}")

        # Check exclusions
        exclusions = eligibility.get("exclusions", [])
        farmer_exclusions = farmer_profile.get("exclusions", [])
        for exc in exclusions:
            if exc in farmer_exclusions:
                score -= 0.5
                missing_criteria.append(f"Excluded: {exc.replace('_', ' ')}")

        eligibility_score = max(0.0, min(1.0, score))

    return SchemeMatch(
        scheme_id=scheme.id,
        scheme_name=scheme.name,
        eligibility_score=eligibility_score,
        benefits_inr=scheme.benefits_inr,
        deadline=scheme.deadline,
        requirements=requirements,
        missing_criteria=missing_criteria,
        application_url=scheme.url,
    )


# ── Credit Scores ────────────────────────────────────────────────────────────

def get_latest_credit_score(db: Session, farmer_id: str) -> Optional[CreditScoreRecord]:
    return (
        db.query(CreditScoreRecord)
        .filter(CreditScoreRecord.farmer_id == farmer_id)
        .order_by(CreditScoreRecord.calculated_at.desc())
        .first()
    )


def save_credit_score(db: Session, farmer_id: str, score: float, components: dict) -> CreditScoreRecord:
    record = CreditScoreRecord(
        farmer_id=farmer_id,
        score=score,
        farm_activity=components.get("farm_activity", 0),
        crop_health=components.get("crop_health", 0),
        market_engagement=components.get("market_engagement", 0),
        peer_reputation=components.get("peer_reputation", 0),
        scheme_compliance=components.get("scheme_compliance", 0),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def credit_record_to_pydantic(record: CreditScoreRecord) -> CreditScore:
    return CreditScore(
        farmer_id=record.farmer_id,
        score=record.score,
        components={
            "farm_activity": record.farm_activity,
            "crop_health": record.crop_health,
            "market_engagement": record.market_engagement,
            "peer_reputation": record.peer_reputation,
            "scheme_compliance": record.scheme_compliance,
        },
        last_updated=record.calculated_at,
    )


# ── Learning Progress ────────────────────────────────────────────────────────

def get_learning_progress(db: Session, farmer_id: str) -> List[LearningProgress]:
    return db.query(LearningProgress).filter(LearningProgress.farmer_id == farmer_id).all()


def mark_content_completed(db: Session, farmer_id: str, content_id: str, topic: str = "") -> LearningProgress:
    existing = (
        db.query(LearningProgress)
        .filter(LearningProgress.farmer_id == farmer_id, LearningProgress.content_id == content_id)
        .first()
    )
    if existing:
        existing.completed = True
        existing.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    progress = LearningProgress(
        farmer_id=farmer_id,
        content_id=content_id,
        topic=topic,
        completed=True,
        completed_at=datetime.utcnow(),
    )
    db.add(progress)
    db.commit()
    db.refresh(progress)
    return progress


# ── Scheme Applications ─────────────────────────────────────────────────────

def create_application(
    db: Session,
    farmer_id: str,
    scheme_id: str,
    status: str = "draft",
    documents_checklist: str = "[]",
    estimated_subsidy: float = 0.0,
    farmer_notes: str = "",
) -> SchemeApplication:
    submitted_at = datetime.utcnow() if status == "submitted" else None
    app = SchemeApplication(
        farmer_id=farmer_id,
        scheme_id=scheme_id,
        status=status,
        documents_checklist_json=documents_checklist,
        estimated_subsidy_inr=estimated_subsidy,
        farmer_notes=farmer_notes,
        submitted_at=submitted_at,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


def get_application(db: Session, app_id: int) -> Optional[SchemeApplication]:
    return db.query(SchemeApplication).filter(SchemeApplication.id == app_id).first()


def get_applications_by_farmer(
    db: Session, farmer_id: str, status: Optional[str] = None
) -> List[SchemeApplication]:
    q = db.query(SchemeApplication).filter(SchemeApplication.farmer_id == farmer_id)
    if status:
        q = q.filter(SchemeApplication.status == status)
    return q.order_by(SchemeApplication.applied_at.desc()).all()


def update_application(db: Session, app: SchemeApplication, **kwargs) -> SchemeApplication:
    for key, value in kwargs.items():
        if hasattr(app, key):
            setattr(app, key, value)
    db.commit()
    db.refresh(app)
    return app


def withdraw_application(db: Session, app: SchemeApplication) -> SchemeApplication:
    app.status = "withdrawn"
    db.commit()
    db.refresh(app)
    return app


def application_to_pydantic(app: SchemeApplication) -> dict:
    checklist = json.loads(app.documents_checklist_json) if app.documents_checklist_json else []
    scheme_name = app.scheme.name if app.scheme else app.scheme_id
    return {
        "id": app.id,
        "farmer_id": app.farmer_id,
        "scheme_id": app.scheme_id,
        "scheme_name": scheme_name,
        "status": app.status,
        "applied_at": str(app.applied_at) if app.applied_at else None,
        "submitted_at": str(app.submitted_at) if app.submitted_at else None,
        "reviewed_at": str(app.reviewed_at) if app.reviewed_at else None,
        "updated_at": str(app.updated_at) if app.updated_at else None,
        "documents_checklist": checklist,
        "estimated_subsidy_inr": app.estimated_subsidy_inr or 0.0,
        "farmer_notes": app.farmer_notes or "",
        "reviewer_notes": app.reviewer_notes or "",
    }


# ── Inventory ───────────────────────────────────────────────────────────────

def create_inventory_item(
    db: Session,
    farmer_id: str,
    name: str,
    category: str,
    quantity: float = 0.0,
    unit: str = "kg",
    alert_threshold: float = 0.0,
    purchase_price: float = 0.0,
    purchase_date: Optional[date] = None,
    expiry_date: Optional[date] = None,
    notes: str = "",
) -> InventoryItem:
    item = InventoryItem(
        farmer_id=farmer_id,
        name=name,
        category=category,
        quantity=quantity,
        unit=unit,
        alert_threshold=alert_threshold,
        purchase_price=purchase_price,
        purchase_date=purchase_date,
        expiry_date=expiry_date,
        notes=notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_inventory_item(db: Session, item_id: int) -> Optional[InventoryItem]:
    return db.query(InventoryItem).filter(InventoryItem.id == item_id).first()


def get_inventory_by_farmer(
    db: Session, farmer_id: str, category: Optional[str] = None
) -> List[InventoryItem]:
    q = db.query(InventoryItem).filter(InventoryItem.farmer_id == farmer_id)
    if category:
        q = q.filter(InventoryItem.category == category)
    return q.order_by(InventoryItem.created_at.desc()).all()


def update_inventory_item(db: Session, item: InventoryItem, **kwargs) -> InventoryItem:
    for key, value in kwargs.items():
        if hasattr(item, key):
            setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def delete_inventory_item(db: Session, item: InventoryItem):
    db.delete(item)
    db.commit()


def adjust_inventory_stock(db: Session, item: InventoryItem, adjustment: float) -> InventoryItem:
    item.quantity = max(0.0, item.quantity + adjustment)
    db.commit()
    db.refresh(item)
    return item


def get_low_stock_items(db: Session, farmer_id: str) -> List[InventoryItem]:
    return (
        db.query(InventoryItem)
        .filter(
            InventoryItem.farmer_id == farmer_id,
            InventoryItem.alert_threshold > 0,
            InventoryItem.quantity <= InventoryItem.alert_threshold,
        )
        .all()
    )


def inventory_item_to_pydantic(item: InventoryItem) -> dict:
    is_low = item.alert_threshold > 0 and item.quantity <= item.alert_threshold
    return {
        "id": item.id,
        "farmer_id": item.farmer_id,
        "name": item.name,
        "category": item.category,
        "quantity": item.quantity,
        "unit": item.unit,
        "alert_threshold": item.alert_threshold,
        "purchase_price": item.purchase_price,
        "purchase_date": str(item.purchase_date) if item.purchase_date else None,
        "expiry_date": str(item.expiry_date) if item.expiry_date else None,
        "notes": item.notes or "",
        "is_low_stock": is_low,
        "created_at": str(item.created_at) if item.created_at else None,
        "updated_at": str(item.updated_at) if item.updated_at else None,
    }


# ── Notifications ───────────────────────────────────────────────────────────

def create_notification(
    db: Session,
    farmer_id: str,
    type: str,
    title: str,
    message: str,
    channel: str = "in_app",
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[str] = None,
) -> Notification:
    notif = Notification(
        farmer_id=farmer_id,
        type=type,
        title=title,
        message=message,
        channel=channel,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


def get_notifications_by_farmer(
    db: Session,
    farmer_id: str,
    type: Optional[str] = None,
    is_read: Optional[bool] = None,
    limit: int = 50,
) -> List[Notification]:
    q = db.query(Notification).filter(Notification.farmer_id == farmer_id)
    if type:
        q = q.filter(Notification.type == type)
    if is_read is not None:
        q = q.filter(Notification.is_read == is_read)
    return q.order_by(Notification.created_at.desc()).limit(limit).all()


def get_unread_count(db: Session, farmer_id: str) -> int:
    return (
        db.query(Notification)
        .filter(Notification.farmer_id == farmer_id, Notification.is_read == False)  # noqa: E712
        .count()
    )


def get_notification(db: Session, notif_id: int) -> Optional[Notification]:
    return db.query(Notification).filter(Notification.id == notif_id).first()


def mark_notification_read(db: Session, notif: Notification) -> Notification:
    notif.is_read = True
    notif.read_at = datetime.utcnow()
    db.commit()
    db.refresh(notif)
    return notif


def mark_all_notifications_read(db: Session, farmer_id: str) -> int:
    count = (
        db.query(Notification)
        .filter(Notification.farmer_id == farmer_id, Notification.is_read == False)  # noqa: E712
        .update({"is_read": True, "read_at": datetime.utcnow()})
    )
    db.commit()
    return count


def delete_notification(db: Session, notif: Notification):
    db.delete(notif)
    db.commit()


def notification_to_pydantic(notif: Notification) -> dict:
    return {
        "id": notif.id,
        "farmer_id": notif.farmer_id,
        "type": notif.type,
        "title": notif.title,
        "message": notif.message,
        "channel": notif.channel or "in_app",
        "is_read": notif.is_read,
        "related_entity_type": notif.related_entity_type,
        "related_entity_id": notif.related_entity_id,
        "created_at": str(notif.created_at) if notif.created_at else None,
        "read_at": str(notif.read_at) if notif.read_at else None,
    }
