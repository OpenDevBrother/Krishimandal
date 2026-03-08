"""
KrishiMandal — SQLAlchemy ORM models for persistence.
Separate from Pydantic models in src/models.py.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from src.database import Base


class Farmer(Base):
    __tablename__ = "farmers"

    id = Column(String(20), primary_key=True)  # e.g. "F1001"
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False, unique=True)
    preferred_language = Column(String(10), default="hi-IN")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    farms = relationship("Farm", back_populates="farmer", cascade="all, delete-orphan")
    credit_scores = relationship("CreditScoreRecord", back_populates="farmer", cascade="all, delete-orphan")
    scheme_applications = relationship("SchemeApplication", back_populates="farmer", cascade="all, delete-orphan")
    learning_progress = relationship("LearningProgress", back_populates="farmer", cascade="all, delete-orphan")
    inventory_items = relationship("InventoryItem", back_populates="farmer", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="farmer", cascade="all, delete-orphan")


class Farm(Base):
    __tablename__ = "farms"

    id = Column(String(30), primary_key=True)  # e.g. "FARM-F1001"
    farmer_id = Column(String(20), ForeignKey("farmers.id"), nullable=False)
    location_lat = Column(Float, default=19.076)
    location_lng = Column(Float, default=72.877)
    area_hectares = Column(Float, nullable=False)
    soil_type = Column(String(20), default="black")
    irrigation_type = Column(String(20), default="rainfed")
    created_at = Column(DateTime, server_default=func.now())

    farmer = relationship("Farmer", back_populates="farms")
    crops = relationship("Crop", back_populates="farm", cascade="all, delete-orphan")
    farm_states = relationship("FarmStateRecord", back_populates="farm", cascade="all, delete-orphan")


class Crop(Base):
    __tablename__ = "crops"

    id = Column(Integer, primary_key=True, autoincrement=True)
    farm_id = Column(String(30), ForeignKey("farms.id"), nullable=False)
    crop_type = Column(String(50), nullable=False)
    variety = Column(String(100), default="")
    planting_date = Column(Date, nullable=False)
    expected_harvest = Column(Date, nullable=True)
    area_hectares = Column(Float, nullable=False)
    growth_stage = Column(String(20), default="germination")
    health_score = Column(Float, default=80.0)
    is_current = Column(Boolean, default=True)
    season = Column(String(30), default="")  # e.g. "Rabi 2025-26"
    yield_quintals = Column(Float, nullable=True)  # filled after harvest

    farm = relationship("Farm", back_populates="crops")


class FarmStateRecord(Base):
    __tablename__ = "farm_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    farm_id = Column(String(30), ForeignKey("farms.id"), nullable=False)
    timestamp = Column(DateTime, server_default=func.now())
    ndvi_mean = Column(Float, default=0.65)
    soil_moisture_pct = Column(Float, default=45.0)
    health_score = Column(Float, default=80.0)
    weather_json = Column(Text, default="{}")  # JSON string of WeatherSnapshot

    farm = relationship("Farm", back_populates="farm_states")


class PriceRecord(Base):
    __tablename__ = "price_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    crop = Column(String(50), nullable=False, index=True)
    mandi = Column(String(100), nullable=False, index=True)
    price = Column(Float, nullable=False)
    recorded_at = Column(DateTime, server_default=func.now(), index=True)


class Scheme(Base):
    __tablename__ = "schemes"

    id = Column(String(20), primary_key=True)  # e.g. "PMKISAN"
    name = Column(String(200), nullable=False)
    benefits_inr = Column(Float, default=0)
    deadline = Column(Date, nullable=True)
    requirements_json = Column(Text, default="[]")  # JSON array of strings
    url = Column(String(500), default="")
    description = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    eligibility_json = Column(Text, default="{}")  # JSON: {land_size_max, income_max, states, ...}
    category = Column(String(50), default="general")
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SchemeApplication(Base):
    __tablename__ = "scheme_applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    farmer_id = Column(String(20), ForeignKey("farmers.id"), nullable=False)
    scheme_id = Column(String(20), ForeignKey("schemes.id"), nullable=False)
    status = Column(String(30), default="draft")  # draft|submitted|under_review|approved|rejected|withdrawn
    applied_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    submitted_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewer_notes = Column(Text, default="")
    documents_checklist_json = Column(Text, default="[]")
    estimated_subsidy_inr = Column(Float, default=0.0)
    farmer_notes = Column(Text, default="")

    farmer = relationship("Farmer", back_populates="scheme_applications")
    scheme = relationship("Scheme")


class CreditScoreRecord(Base):
    __tablename__ = "credit_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    farmer_id = Column(String(20), ForeignKey("farmers.id"), nullable=False)
    score = Column(Float, nullable=False)
    farm_activity = Column(Float, default=0)
    crop_health = Column(Float, default=0)
    market_engagement = Column(Float, default=0)
    peer_reputation = Column(Float, default=0)
    scheme_compliance = Column(Float, default=0)
    calculated_at = Column(DateTime, server_default=func.now())

    farmer = relationship("Farmer", back_populates="credit_scores")


class LearningProgress(Base):
    __tablename__ = "learning_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    farmer_id = Column(String(20), ForeignKey("farmers.id"), nullable=False)
    content_id = Column(String(30), nullable=False)
    topic = Column(String(50), default="")
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)

    farmer = relationship("Farmer", back_populates="learning_progress")


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    farmer_id = Column(String(20), ForeignKey("farmers.id"), nullable=False)
    name = Column(String(200), nullable=False)
    category = Column(String(30), nullable=False)  # seed|fertilizer|pesticide|harvest|equipment
    quantity = Column(Float, default=0.0)
    unit = Column(String(20), default="kg")  # kg|liters|units|quintals|bags
    alert_threshold = Column(Float, default=0.0)
    purchase_price = Column(Float, default=0.0)
    purchase_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    notes = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    farmer = relationship("Farmer", back_populates="inventory_items")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    farmer_id = Column(String(20), ForeignKey("farmers.id"), nullable=False)
    type = Column(String(30), nullable=False)  # scheme_deadline|price_alert|pest_warning|application_update|inventory_alert|weather_alert|general
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    channel = Column(String(20), default="in_app")
    is_read = Column(Boolean, default=False)
    related_entity_type = Column(String(30), nullable=True)  # scheme|application|inventory_item|crop
    related_entity_id = Column(String(30), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    read_at = Column(DateTime, nullable=True)

    farmer = relationship("Farmer", back_populates="notifications")
