"""
KrishiMandal — FastAPI Application
Exposes the multi-agent orchestrator as REST endpoints.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.auth import verify_api_key
from src.config import settings
from src.database import get_db, init_db
from src.exceptions import KrishiMandalError
from src.middleware import RequestIdMiddleware, RequestLoggingMiddleware
from src.models import (
    AddCropRequest,
    AdjustStockRequest,
    CreateApplicationRequest,
    CreateFarmRequest,
    CreateInventoryRequest,
    SimulateRequest,
    UpdateApplicationRequest,
    UpdateFarmRequest,
    UpdateInventoryRequest,
)
from src.orchestrator import SupervisorOrchestrator
from src.routers.voice import router as voice_router
from src.routers.whatsapp import router as whatsapp_router

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(name)-28s | %(levelname)-5s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="KrishiMandal API",
    description="Multi-Agent AI Platform for Smallholder Farmers in India",
    version="0.3.0",
)

# Middleware (order matters — outermost first)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Exception handlers ──────────────────────────────────────────────────────

@app.exception_handler(KrishiMandalError)
async def krishimandal_error_handler(request: Request, exc: KrishiMandalError):
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "request_id": req_id},
    )


# ── Startup ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    """Initialise database tables and background scheduler on startup."""
    init_db()
    logger.info("Database tables created/verified.")
    from src.events import setup_notification_handlers
    setup_notification_handlers()
    # Warn about missing keys
    if not settings.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set — LLM responses will use fallback.")
    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set — embeddings will use fallback.")
    if not settings.PINECONE_API_KEY:
        logger.warning("PINECONE_API_KEY not set — vector store will use fallback.")
    # Start background scheduler
    try:
        from src.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        logger.warning("Scheduler startup failed: %s", e)


@app.on_event("shutdown")
def on_shutdown():
    """Stop background scheduler on shutdown."""
    try:
        from src.scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass


# ── Include routers ──────────────────────────────────────────────────────────
app.include_router(voice_router, prefix="/voice", tags=["Voice"])
app.include_router(whatsapp_router, prefix="/whatsapp", tags=["WhatsApp"])

orchestrator = SupervisorOrchestrator()


# ── Request / Response schemas ───────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    farmer_id: str = "F1001"
    language: str = "hi-IN"
    context: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    query: str
    farmer_id: str
    language: str
    agents_invoked: list
    final_response: str
    processing_time_ms: int


class AgentListItem(BaseModel):
    name: str
    description: str


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC ENDPOINTS (no auth)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["System"])
def root():
    return {
        "platform": "KrishiMandal",
        "version": "0.3.0",
        "status": "running",
        "dummy_data_mode": settings.USE_DUMMY_DATA,
        "agents": len(orchestrator.agents),
        "services": {
            "llm": "groq" if orchestrator.llm.is_available else "fallback",
            "embeddings": "gemini" if settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your_") else "fallback",
            "vector_store": "pinecone" if settings.PINECONE_API_KEY and not settings.PINECONE_API_KEY.startswith("your_") else "fallback",
        },
    }


@app.get("/health", tags=["System"])
def health_check(db: Session = Depends(get_db)):
    """Enhanced health check — verifies DB connectivity and service status."""
    from src.services.llm_service import get_llm
    from src.services.embeddings_service import get_embeddings
    from src.services.vector_store import get_vector_store

    # DB check
    db_ok = True
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    return {
        "status": "healthy",
        "database": "connected" if db_ok else "error",
        "llm": "available" if get_llm().is_available else "unavailable",
        "embeddings": "available" if get_embeddings().is_available else "unavailable",
        "vector_store": "available" if get_vector_store().is_available else "unavailable",
        "dummy_data_mode": settings.USE_DUMMY_DATA,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  AUTHENTICATED ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/services/status", tags=["System"], dependencies=[Depends(verify_api_key)])
def service_status():
    """Check the status of all AI services (Groq, Gemini, Pinecone)."""
    from src.services.llm_service import get_llm
    from src.services.embeddings_service import get_embeddings
    from src.services.vector_store import get_vector_store

    llm = get_llm()
    embeddings = get_embeddings()
    vector_store = get_vector_store()

    return {
        "llm": {
            "provider": "Groq",
            "model": settings.GROQ_MODEL_ID,
            "available": llm.is_available,
            "note": "Used for response synthesis and RAG answer generation",
        },
        "embeddings": {
            "provider": "Google Gemini",
            "model": settings.GEMINI_EMBEDDING_MODEL,
            "available": embeddings.is_available,
            "note": "Used for encoding queries and documents for RAG",
        },
        "vector_store": {
            "provider": "Pinecone",
            "index": settings.PINECONE_INDEX_NAME,
            "available": vector_store.is_available,
            "stats": vector_store.get_index_stats() if vector_store.is_available else {},
            "note": "Used for storing and retrieving RAG knowledge documents",
        },
        "dummy_data_mode": settings.USE_DUMMY_DATA,
    }


# ── Query ────────────────────────────────────────────────────────────────────

@app.post("/query", response_model=QueryResponse, tags=["Query"], dependencies=[Depends(verify_api_key)])
def handle_query(req: QueryRequest):
    """Main endpoint — send a farmer query and get a routed, multi-agent response."""
    logger.info("Incoming query from %s: %s", req.farmer_id, req.query[:100])
    try:
        result = orchestrator.route_query(
            query=req.query,
            farmer_id=req.farmer_id,
            language=req.language,
            context=req.context,
        )
        return QueryResponse(
            query=result.query,
            farmer_id=result.farmer_id,
            language=result.language,
            agents_invoked=result.agents_invoked,
            final_response=result.final_response,
            processing_time_ms=result.processing_time_ms,
        )
    except Exception as e:
        logger.error("Query failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents", response_model=list[AgentListItem], tags=["Query"], dependencies=[Depends(verify_api_key)])
def list_agents():
    """List all registered sub-agents."""
    return orchestrator.list_agents()


# ── Farm CRUD ────────────────────────────────────────────────────────────────

@app.get("/farm/{farmer_id}", tags=["Farm"], dependencies=[Depends(verify_api_key)])
def get_farm_profile(farmer_id: str):
    """Retrieve the farm profile for a farmer."""
    dt = orchestrator.agents["digital_twin"]
    profile = dt.get_farm_profile(farmer_id)
    return profile.model_dump(mode="json")


@app.post("/farm", tags=["Farm"], dependencies=[Depends(verify_api_key)])
def create_farm_profile(req: CreateFarmRequest, db: Session = Depends(get_db)):
    """Create a new farmer + farm profile."""
    from src.repositories import create_farm, create_farmer, get_farmer

    if get_farmer(db, req.farmer_id):
        raise HTTPException(status_code=409, detail=f"Farmer {req.farmer_id} already exists.")

    farmer = create_farmer(db, req.farmer_id, req.farmer_name, req.phone, req.preferred_language)
    farm = create_farm(
        db,
        farm_id=f"FARM-{req.farmer_id}",
        farmer_id=req.farmer_id,
        area_hectares=req.area_hectares,
        soil_type=req.soil_type,
        irrigation_type=req.irrigation_type,
        lat=req.location_lat,
        lng=req.location_lng,
    )
    return {
        "message": "Farm profile created successfully.",
        "farmer_id": farmer.id,
        "farm_id": farm.id,
    }


@app.put("/farm/{farmer_id}", tags=["Farm"], dependencies=[Depends(verify_api_key)])
def update_farm_profile(farmer_id: str, req: UpdateFarmRequest, db: Session = Depends(get_db)):
    """Update an existing farm profile."""
    from src.repositories import get_farm_by_farmer, get_farmer, update_farm

    farmer = get_farmer(db, farmer_id)
    if not farmer:
        raise HTTPException(status_code=404, detail=f"Farmer {farmer_id} not found.")

    # Update farmer fields
    if req.farmer_name is not None:
        farmer.name = req.farmer_name
    if req.phone is not None:
        farmer.phone = req.phone
    if req.preferred_language is not None:
        farmer.preferred_language = req.preferred_language

    farm = get_farm_by_farmer(db, farmer_id)
    if farm:
        farm_updates = {}
        if req.area_hectares is not None:
            farm_updates["area_hectares"] = req.area_hectares
        if req.soil_type is not None:
            farm_updates["soil_type"] = req.soil_type
        if req.irrigation_type is not None:
            farm_updates["irrigation_type"] = req.irrigation_type
        if req.location_lat is not None:
            farm_updates["location_lat"] = req.location_lat
        if req.location_lng is not None:
            farm_updates["location_lng"] = req.location_lng
        if farm_updates:
            update_farm(db, farm, **farm_updates)

    db.commit()
    return {"message": "Farm profile updated.", "farmer_id": farmer_id}


@app.delete("/farm/{farmer_id}", tags=["Farm"], dependencies=[Depends(verify_api_key)])
def delete_farm_profile(farmer_id: str, db: Session = Depends(get_db)):
    """Delete a farmer and all associated data."""
    from src.repositories import delete_farmer

    if not delete_farmer(db, farmer_id):
        raise HTTPException(status_code=404, detail=f"Farmer {farmer_id} not found.")
    return {"message": "Farmer and all associated data deleted.", "farmer_id": farmer_id}


@app.post("/farm/{farmer_id}/crops", tags=["Farm"], dependencies=[Depends(verify_api_key)])
def add_crop_to_farm(farmer_id: str, req: AddCropRequest, db: Session = Depends(get_db)):
    """Add a crop to the farmer's farm."""
    from src.repositories import add_crop, get_farm_by_farmer

    farm = get_farm_by_farmer(db, farmer_id)
    if not farm:
        raise HTTPException(status_code=404, detail=f"Farm for farmer {farmer_id} not found.")

    crop = add_crop(
        db,
        farm_id=farm.id,
        crop_type=req.crop_type,
        area_hectares=req.area_hectares,
        variety=req.variety,
        planting_date=req.planting_date,
        expected_harvest=req.expected_harvest,
        growth_stage=req.growth_stage,
    )
    return {"message": "Crop added.", "crop_id": crop.id, "farm_id": farm.id}


@app.get("/farm/{farmer_id}/state", tags=["Farm"], dependencies=[Depends(verify_api_key)])
def get_farm_state(farmer_id: str):
    """Get current farm state (NDVI, moisture, weather)."""
    dt = orchestrator.agents["digital_twin"]
    state = dt.get_farm_state(f"FARM-{farmer_id}")
    return state.model_dump(mode="json")


@app.get("/farm/{farmer_id}/health", tags=["Farm"], dependencies=[Depends(verify_api_key)])
def get_crop_health(farmer_id: str):
    """Get crop health score and components."""
    cm = orchestrator.agents["crop_management"]
    health = cm.compute_health_score(f"FARM-{farmer_id}")
    return health.model_dump(mode="json")


@app.get("/farm/{farmer_id}/schemes", tags=["Schemes"], dependencies=[Depends(verify_api_key)])
def get_scheme_matches(farmer_id: str):
    """Get matched government schemes for the farmer."""
    sc = orchestrator.agents["scheme_credit"]
    matches = sc.match_schemes(farmer_id)
    return [m.model_dump(mode="json") for m in matches]


@app.post("/farm/{farmer_id}/simulate", tags=["Farm"], dependencies=[Depends(verify_api_key)])
def simulate_scenario(farmer_id: str, req: SimulateRequest):
    """Run a what-if scenario simulation on the farmer's farm."""
    dt = orchestrator.agents["digital_twin"]
    result = dt.simulate_scenario(farmer_id, req.scenario)
    return result


# ── Prices ───────────────────────────────────────────────────────────────────

@app.get("/price/{crop}", tags=["Prices"], dependencies=[Depends(verify_api_key)])
def get_price_forecast(crop: str, mandi: str | None = None):
    """Get price forecast for a crop."""
    pp = orchestrator.agents["price_predictor"]
    forecast = pp.forecast_price(crop, mandi)
    return forecast.model_dump()


@app.get("/price/{crop}/history", tags=["Prices"], dependencies=[Depends(verify_api_key)])
def get_price_history(crop: str, mandi: str | None = None, days: int = 30):
    """Get historical price records for a crop."""
    pp = orchestrator.agents["price_predictor"]
    history = pp.get_price_history(crop, mandi, days)
    return {"crop": crop, "mandi": mandi, "days": days, "records": history}


# ── Supply Chain ─────────────────────────────────────────────────────────────

@app.get("/farm/{farmer_id}/harvest-plan", tags=["Supply Chain"], dependencies=[Depends(verify_api_key)])
def get_harvest_plan(farmer_id: str, crop: str = "wheat"):
    """Generate a pre-harvest logistics plan."""
    sc_agent = orchestrator.agents["supply_chain"]
    plan = sc_agent.generate_harvest_plan(f"FARM-{farmer_id}", crop)
    return plan.model_dump(mode="json")


# ── Learning ─────────────────────────────────────────────────────────────────

@app.get("/learning/content", tags=["Learning"], dependencies=[Depends(verify_api_key)])
def get_learning_content(topic: str | None = None, language: str = "hi-IN"):
    """Browse learning content by topic and language."""
    lp = orchestrator.agents["learning_platform"]
    contents = lp.recommend_content("anonymous", topic, language)
    return [c.model_dump() for c in contents]


# ── RAG ──────────────────────────────────────────────────────────────────────

@app.post("/rag/ask", tags=["RAG"], dependencies=[Depends(verify_api_key)])
def rag_ask(req: QueryRequest):
    """Ask a question to the RAG knowledge base (Pinecone + Gemini + Groq)."""
    lp = orchestrator.agents["learning_platform"]
    result = lp.rag_answer(req.query)
    return result


@app.post("/rag/ingest", tags=["RAG"], dependencies=[Depends(verify_api_key)])
def rag_ingest():
    """Trigger knowledge ingestion into Pinecone (admin endpoint)."""
    try:
        from src.ingest_knowledge import ingest_knowledge
        ingest_knowledge()
        return {"status": "success", "message": "Knowledge ingestion completed"}
    except Exception as e:
        logger.error("Ingestion failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Document Upload & OCR ────────────────────────────────────────────────────

@app.post("/documents/upload", tags=["Documents"], dependencies=[Depends(verify_api_key)])
async def upload_document(farmer_id: str = "F1001"):
    """
    Upload a document or crop photo.
    Requires python-multipart. Send as multipart/form-data with 'file' field.
    """
    from src.services.file_storage import get_file_storage

    storage = get_file_storage()
    files = storage.list_files(farmer_id)
    return {
        "message": "Upload endpoint ready. POST a file using multipart/form-data.",
        "farmer_id": farmer_id,
        "existing_files": files,
        "upload_dir": settings.UPLOAD_DIR,
    }


@app.post("/documents/ocr", tags=["Documents"], dependencies=[Depends(verify_api_key)])
def ocr_document(image_path: str = ""):
    """Run OCR on an uploaded document image."""
    from src.services.ocr_service import get_ocr_service

    ocr = get_ocr_service()
    result = ocr.extract_text(image_path)
    return result


# ── Scheme Applications ─────────────────────────────────────────────────────

@app.post("/farm/{farmer_id}/applications", tags=["Applications"], dependencies=[Depends(verify_api_key)])
def create_application(farmer_id: str, req: CreateApplicationRequest, db: Session = Depends(get_db)):
    """Create a scheme application (draft or submit directly)."""
    import json as _json
    from src.repositories import create_application as repo_create_app, get_farmer
    from src.db_models import Scheme
    from src.events import APPLICATION_SUBMITTED, event_bus

    farmer = get_farmer(db, farmer_id)
    if not farmer:
        raise HTTPException(status_code=404, detail=f"Farmer {farmer_id} not found.")

    scheme = db.query(Scheme).filter(Scheme.id == req.scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Scheme {req.scheme_id} not found.")

    # Build documents checklist from scheme requirements
    requirements = _json.loads(scheme.requirements_json) if scheme.requirements_json else []
    checklist = [{"name": r, "uploaded": False, "file_path": ""} for r in requirements]

    status = "submitted" if req.submit_directly else "draft"
    app = repo_create_app(
        db,
        farmer_id=farmer_id,
        scheme_id=req.scheme_id,
        status=status,
        documents_checklist=_json.dumps(checklist),
        estimated_subsidy=scheme.benefits_inr or 0.0,
        farmer_notes=req.farmer_notes,
    )

    if status == "submitted":
        event_bus.publish(APPLICATION_SUBMITTED, {
            "farmer_id": farmer_id,
            "scheme_id": req.scheme_id,
            "application_id": app.id,
        })

    from src.repositories import application_to_pydantic
    return application_to_pydantic(app)


@app.get("/farm/{farmer_id}/applications", tags=["Applications"], dependencies=[Depends(verify_api_key)])
def list_applications(farmer_id: str, status: str | None = None, db: Session = Depends(get_db)):
    """List scheme applications for a farmer."""
    from src.repositories import get_applications_by_farmer, application_to_pydantic
    apps = get_applications_by_farmer(db, farmer_id, status=status)
    return [application_to_pydantic(a) for a in apps]


@app.get("/farm/{farmer_id}/applications/{app_id}", tags=["Applications"], dependencies=[Depends(verify_api_key)])
def get_application_detail(farmer_id: str, app_id: int, db: Session = Depends(get_db)):
    """Get a single application."""
    from src.repositories import get_application, application_to_pydantic
    app = get_application(db, app_id)
    if not app or app.farmer_id != farmer_id:
        raise HTTPException(status_code=404, detail="Application not found.")
    return application_to_pydantic(app)


@app.put("/farm/{farmer_id}/applications/{app_id}", tags=["Applications"], dependencies=[Depends(verify_api_key)])
def update_application_endpoint(farmer_id: str, app_id: int, req: UpdateApplicationRequest, db: Session = Depends(get_db)):
    """Submit a draft application or update notes/checklist."""
    import json as _json
    from datetime import datetime
    from src.repositories import get_application, update_application, application_to_pydantic
    from src.events import APPLICATION_SUBMITTED, event_bus

    app = get_application(db, app_id)
    if not app or app.farmer_id != farmer_id:
        raise HTTPException(status_code=404, detail="Application not found.")

    updates = {}
    if req.farmer_notes is not None:
        updates["farmer_notes"] = req.farmer_notes
    if req.documents_checklist is not None:
        updates["documents_checklist_json"] = _json.dumps([d.model_dump() for d in req.documents_checklist])

    if req.action == "submit" and app.status == "draft":
        updates["status"] = "submitted"
        updates["submitted_at"] = datetime.utcnow()

    app = update_application(db, app, **updates)

    if updates.get("status") == "submitted":
        event_bus.publish(APPLICATION_SUBMITTED, {
            "farmer_id": farmer_id,
            "scheme_id": app.scheme_id,
            "application_id": app.id,
        })

    return application_to_pydantic(app)


@app.delete("/farm/{farmer_id}/applications/{app_id}", tags=["Applications"], dependencies=[Depends(verify_api_key)])
def withdraw_application_endpoint(farmer_id: str, app_id: int, db: Session = Depends(get_db)):
    """Withdraw an application (not if already approved/rejected)."""
    from src.repositories import get_application, withdraw_application, application_to_pydantic
    from src.events import APPLICATION_STATUS_CHANGED, event_bus

    app = get_application(db, app_id)
    if not app or app.farmer_id != farmer_id:
        raise HTTPException(status_code=404, detail="Application not found.")
    if app.status in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail=f"Cannot withdraw application with status '{app.status}'.")

    app = withdraw_application(db, app)
    event_bus.publish(APPLICATION_STATUS_CHANGED, {
        "farmer_id": farmer_id,
        "application_id": app.id,
        "status": "withdrawn",
    })
    return application_to_pydantic(app)


# ── Inventory Management ────────────────────────────────────────────────────

@app.post("/farm/{farmer_id}/inventory", tags=["Inventory"], dependencies=[Depends(verify_api_key)])
def add_inventory_item(farmer_id: str, req: CreateInventoryRequest, db: Session = Depends(get_db)):
    """Add an inventory item."""
    from src.repositories import create_inventory_item, get_farmer, inventory_item_to_pydantic

    farmer = get_farmer(db, farmer_id)
    if not farmer:
        raise HTTPException(status_code=404, detail=f"Farmer {farmer_id} not found.")

    item = create_inventory_item(
        db,
        farmer_id=farmer_id,
        name=req.name,
        category=req.category,
        quantity=req.quantity,
        unit=req.unit,
        alert_threshold=req.alert_threshold,
        purchase_price=req.purchase_price,
        purchase_date=req.purchase_date,
        expiry_date=req.expiry_date,
        notes=req.notes,
    )
    return inventory_item_to_pydantic(item)


@app.get("/farm/{farmer_id}/inventory", tags=["Inventory"], dependencies=[Depends(verify_api_key)])
def list_inventory(farmer_id: str, category: str | None = None, db: Session = Depends(get_db)):
    """List inventory items for a farmer."""
    from src.repositories import get_inventory_by_farmer, inventory_item_to_pydantic
    items = get_inventory_by_farmer(db, farmer_id, category=category)
    return [inventory_item_to_pydantic(i) for i in items]


@app.get("/farm/{farmer_id}/inventory/alerts", tags=["Inventory"], dependencies=[Depends(verify_api_key)])
def get_inventory_alerts(farmer_id: str, db: Session = Depends(get_db)):
    """Get low-stock alerts."""
    from src.repositories import get_low_stock_items, inventory_item_to_pydantic
    items = get_low_stock_items(db, farmer_id)
    return [inventory_item_to_pydantic(i) for i in items]


@app.get("/farm/{farmer_id}/inventory/{item_id}", tags=["Inventory"], dependencies=[Depends(verify_api_key)])
def get_inventory_item_detail(farmer_id: str, item_id: int, db: Session = Depends(get_db)):
    """Get a single inventory item."""
    from src.repositories import get_inventory_item, inventory_item_to_pydantic
    item = get_inventory_item(db, item_id)
    if not item or item.farmer_id != farmer_id:
        raise HTTPException(status_code=404, detail="Inventory item not found.")
    return inventory_item_to_pydantic(item)


@app.put("/farm/{farmer_id}/inventory/{item_id}", tags=["Inventory"], dependencies=[Depends(verify_api_key)])
def update_inventory_item_endpoint(farmer_id: str, item_id: int, req: UpdateInventoryRequest, db: Session = Depends(get_db)):
    """Update an inventory item."""
    from src.repositories import get_inventory_item, update_inventory_item, inventory_item_to_pydantic
    item = get_inventory_item(db, item_id)
    if not item or item.farmer_id != farmer_id:
        raise HTTPException(status_code=404, detail="Inventory item not found.")

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    item = update_inventory_item(db, item, **updates)
    return inventory_item_to_pydantic(item)


@app.delete("/farm/{farmer_id}/inventory/{item_id}", tags=["Inventory"], dependencies=[Depends(verify_api_key)])
def delete_inventory_item_endpoint(farmer_id: str, item_id: int, db: Session = Depends(get_db)):
    """Delete an inventory item."""
    from src.repositories import get_inventory_item, delete_inventory_item
    item = get_inventory_item(db, item_id)
    if not item or item.farmer_id != farmer_id:
        raise HTTPException(status_code=404, detail="Inventory item not found.")
    delete_inventory_item(db, item)
    return {"message": "Inventory item deleted.", "item_id": item_id}


@app.post("/farm/{farmer_id}/inventory/{item_id}/adjust", tags=["Inventory"], dependencies=[Depends(verify_api_key)])
def adjust_inventory_stock(farmer_id: str, item_id: int, req: AdjustStockRequest, db: Session = Depends(get_db)):
    """Quick stock adjustment (+/-)."""
    from src.repositories import get_inventory_item, adjust_inventory_stock as repo_adjust, inventory_item_to_pydantic
    from src.events import INVENTORY_LOW_STOCK, event_bus

    item = get_inventory_item(db, item_id)
    if not item or item.farmer_id != farmer_id:
        raise HTTPException(status_code=404, detail="Inventory item not found.")

    item = repo_adjust(db, item, req.adjustment)

    # Fire low stock event if threshold breached
    if item.alert_threshold > 0 and item.quantity <= item.alert_threshold:
        event_bus.publish(INVENTORY_LOW_STOCK, {
            "farmer_id": farmer_id,
            "item_id": item.id,
            "item_name": item.name,
            "quantity": item.quantity,
            "unit": item.unit,
        })

    return inventory_item_to_pydantic(item)


# ── Notifications ───────────────────────────────────────────────────────────

@app.get("/farm/{farmer_id}/notifications", tags=["Notifications"], dependencies=[Depends(verify_api_key)])
def list_notifications(farmer_id: str, type: str | None = None, is_read: bool | None = None, db: Session = Depends(get_db)):
    """List notifications for a farmer."""
    from src.repositories import get_notifications_by_farmer, notification_to_pydantic
    notifs = get_notifications_by_farmer(db, farmer_id, type=type, is_read=is_read)
    return [notification_to_pydantic(n) for n in notifs]


@app.get("/farm/{farmer_id}/notifications/unread-count", tags=["Notifications"], dependencies=[Depends(verify_api_key)])
def get_unread_notification_count(farmer_id: str, db: Session = Depends(get_db)):
    """Get unread notification count."""
    from src.repositories import get_unread_count
    count = get_unread_count(db, farmer_id)
    return {"farmer_id": farmer_id, "unread_count": count}


@app.put("/farm/{farmer_id}/notifications/read-all", tags=["Notifications"], dependencies=[Depends(verify_api_key)])
def mark_all_read(farmer_id: str, db: Session = Depends(get_db)):
    """Mark all notifications as read."""
    from src.repositories import mark_all_notifications_read
    count = mark_all_notifications_read(db, farmer_id)
    return {"farmer_id": farmer_id, "marked_read": count}


@app.put("/farm/{farmer_id}/notifications/{notif_id}/read", tags=["Notifications"], dependencies=[Depends(verify_api_key)])
def mark_notification_read_endpoint(farmer_id: str, notif_id: int, db: Session = Depends(get_db)):
    """Mark a single notification as read."""
    from src.repositories import get_notification, mark_notification_read, notification_to_pydantic
    notif = get_notification(db, notif_id)
    if not notif or notif.farmer_id != farmer_id:
        raise HTTPException(status_code=404, detail="Notification not found.")
    notif = mark_notification_read(db, notif)
    return notification_to_pydantic(notif)


@app.delete("/farm/{farmer_id}/notifications/{notif_id}", tags=["Notifications"], dependencies=[Depends(verify_api_key)])
def delete_notification_endpoint(farmer_id: str, notif_id: int, db: Session = Depends(get_db)):
    """Delete a notification."""
    from src.repositories import get_notification, delete_notification
    notif = get_notification(db, notif_id)
    if not notif or notif.farmer_id != farmer_id:
        raise HTTPException(status_code=404, detail="Notification not found.")
    delete_notification(db, notif)
    return {"message": "Notification deleted.", "notif_id": notif_id}
