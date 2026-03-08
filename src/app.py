"""
KrishiMandal — FastAPI Application
Exposes the multi-agent orchestrator as REST endpoints.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config import settings
from src.orchestrator import SupervisorOrchestrator

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
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "platform": "KrishiMandal",
        "version": "0.2.0",
        "status": "running",
        "dummy_data_mode": settings.USE_DUMMY_DATA,
        "agents": len(orchestrator.agents),
        "services": {
            "llm": "groq" if orchestrator.llm.is_available else "fallback",
            "embeddings": "gemini" if settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your_") else "fallback",
            "vector_store": "pinecone" if settings.PINECONE_API_KEY and not settings.PINECONE_API_KEY.startswith("your_") else "fallback",
        },
    }


@app.get("/services/status")
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
        "note": (
            "USE_DUMMY_DATA controls domain data (farms, prices, schemes). "
            "LLM, Embeddings, and Vector Store are ALWAYS active when configured."
        ),
    }


@app.post("/query", response_model=QueryResponse)
def handle_query(req: QueryRequest):
    """
    Main endpoint — send a farmer query and get a routed, multi-agent response.
    """
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


@app.get("/agents", response_model=list[AgentListItem])
def list_agents():
    """List all registered sub-agents."""
    return orchestrator.list_agents()


@app.get("/farm/{farmer_id}")
def get_farm_profile(farmer_id: str):
    """Retrieve the farm profile for a farmer."""
    dt = orchestrator.agents["digital_twin"]
    profile = dt.get_farm_profile(farmer_id)
    return profile.model_dump(mode="json")


@app.get("/farm/{farmer_id}/state")
def get_farm_state(farmer_id: str):
    """Get current farm state (NDVI, moisture, weather)."""
    dt = orchestrator.agents["digital_twin"]
    state = dt.get_farm_state(f"FARM-{farmer_id}")
    return state.model_dump(mode="json")


@app.get("/farm/{farmer_id}/health")
def get_crop_health(farmer_id: str):
    """Get crop health score and components."""
    cm = orchestrator.agents["crop_management"]
    health = cm.compute_health_score(f"FARM-{farmer_id}")
    return health.model_dump(mode="json")


@app.get("/farm/{farmer_id}/schemes")
def get_scheme_matches(farmer_id: str):
    """Get matched government schemes for the farmer."""
    sc = orchestrator.agents["scheme_credit"]
    matches = sc.match_schemes(farmer_id)
    return [m.model_dump(mode="json") for m in matches]


@app.get("/price/{crop}")
def get_price_forecast(crop: str, mandi: str | None = None):
    """Get price forecast for a crop."""
    pp = orchestrator.agents["price_predictor"]
    forecast = pp.forecast_price(crop, mandi)
    return forecast.model_dump()


@app.get("/farm/{farmer_id}/harvest-plan")
def get_harvest_plan(farmer_id: str, crop: str = "wheat"):
    """Generate a pre-harvest logistics plan."""
    sc_agent = orchestrator.agents["supply_chain"]
    plan = sc_agent.generate_harvest_plan(f"FARM-{farmer_id}", crop)
    return plan.model_dump(mode="json")


@app.post("/rag/ask")
def rag_ask(req: QueryRequest):
    """Ask a question to the RAG knowledge base (Pinecone + Gemini + Groq)."""
    lp = orchestrator.agents["learning_platform"]
    result = lp.rag_answer(req.query)
    return result


@app.post("/rag/ingest")
def rag_ingest():
    """Trigger knowledge ingestion into Pinecone (admin endpoint)."""
    try:
        from src.ingest_knowledge import ingest_knowledge
        ingest_knowledge()
        return {"status": "success", "message": "Knowledge ingestion completed"}
    except Exception as e:
        logger.error("Ingestion failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
