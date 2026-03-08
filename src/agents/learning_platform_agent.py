"""
KrishiMandal — Farmer Learning Platform Agent
Delivers personalised learning content, answers questions via
RAG (Pinecone + Gemini embeddings + Groq LLM), and provides
community features.

RAG pipeline is ALWAYS active (uses Groq/Gemini/Pinecone regardless
of USE_DUMMY_DATA). Falls back to local keyword matching if services
are unavailable.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from src.config import settings
from src.models import AgentResponse, LearningContent
from src.services.llm_service import get_llm
from src.services.embeddings_service import get_embeddings
from src.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)


# ── Local RAG knowledge (fallback when Pinecone/Gemini are unavailable) ──────

_RAG_KNOWLEDGE: Dict[str, Dict[str, str]] = {
    "pest_control": {
        "answer": (
            "Integrated Pest Management (IPM) is the recommended approach. "
            "Step 1: Monitor fields weekly for pest signs. "
            "Step 2: Use pheromone traps and yellow sticky traps for early detection. "
            "Step 3: Apply neem-based bio-pesticides first. "
            "Step 4: Use chemical pesticides only when economic threshold is crossed. "
            "Avoid banned chemicals like DDT, endosulfan, and monocrotophos."
        ),
        "source": "ICAR Technical Bulletin No. 45 — Integrated Pest Management for Field Crops",
    },
    "organic_farming": {
        "answer": (
            "To start organic farming: "
            "1. Stop chemical inputs immediately and begin a 3-year conversion period. "
            "2. Prepare compost using farm waste, cow dung, and crop residue. "
            "3. Use Jeevamrutha (fermented microbial culture) for soil enrichment. "
            "4. Apply Panchagavya as foliar spray. "
            "5. Use green manuring with dhaincha or sun hemp. "
            "6. Get certified through NPOP (National Programme for Organic Production). "
            "Premium: Organic produce fetches 20-40% higher prices."
        ),
        "source": "NPOP Guidelines, APEDA — Organic Farming Practices Manual",
    },
    "drip_irrigation": {
        "answer": (
            "Drip irrigation saves 30-50% water and increases yield by 20-30%. "
            "Setup: Mainline → Sub-mainline → Laterals → Drippers. "
            "Spacing: 30-60 cm between drippers depending on crop. "
            "Fertigation: Mix water-soluble fertilisers directly into the drip system. "
            "Government subsidy: 55-70% under PM-KUSUM and PMKSY-PDMC. "
            "Maintenance: Flush lines monthly, check filters weekly."
        ),
        "source": "IARI Extension Bulletin — Micro-Irrigation for Indian Agriculture",
    },
    "soil_health": {
        "answer": (
            "Get a Soil Health Card (free from government). Test every 2 years. "
            "Key parameters: pH, EC, Organic Carbon, N-P-K, micro-nutrients. "
            "Ideal pH for most crops: 6.0-7.5. "
            "Improve organic carbon: Add FYM (5-10 tonnes/ha), vermi-compost, green manure. "
            "Crop rotation with legumes fixes nitrogen naturally. "
            "Avoid over-tilling — adopt zero-till or minimum tillage."
        ),
        "source": "Soil Health Card Scheme — Dept. of Agriculture & Farmers' Welfare",
    },
    "water_management": {
        "answer": (
            "Rainwater harvesting: Build farm ponds (30×30×3m captures ~27 lakh litres). "
            "Subsidy available under MGNREGA and PMKSY. "
            "Mulching reduces evaporation by 25-30%. Use crop residue or plastic mulch. "
            "Schedule irrigation based on crop ET (evapotranspiration) — "
            "wheat needs 450mm, cotton 700mm, sugarcane 1800mm total. "
            "Use tensiometer or soil moisture sensor for precision watering."
        ),
        "source": "CWRDM & ICAR — Water Management in Rainfed Agriculture",
    },
    "pm_kisan": {
        "answer": (
            "PM-KISAN provides ₹6,000/year in 3 instalments of ₹2,000 directly to bank account. "
            "Eligibility: All land-holding farmer families. "
            "Excluded: Institutional landholders, income-tax payers, professionals. "
            "Documents: Aadhaar, bank account, land records. "
            "Apply at pmkisan.gov.in or through CSC (Common Service Centre). "
            "Check status: Enter Aadhaar or account number on the portal."
        ),
        "source": "PM-KISAN Official Guidelines — Ministry of Agriculture",
    },
    "pmfby": {
        "answer": (
            "PM Fasal Bima Yojana (PMFBY) provides crop insurance at very low premiums. "
            "Premium: Kharif 2%, Rabi 1.5%, Commercial/Horticulture 5%. "
            "Coverage: Natural calamities, pest/disease, post-harvest losses (14 days). "
            "Claim process: Report crop loss within 72 hours via app or toll-free number. "
            "Assessment: Technology-based (satellite, drone, smartphone) for faster settlement. "
            "Enrolment: Via bank, CSC, or PMFBY portal during season window."
        ),
        "source": "PMFBY Operational Guidelines — Dept. of Agriculture",
    },
}


class LearningPlatformAgent:
    """Agent responsible for educational content delivery and RAG-based Q&A."""

    NAME = "learning_platform"

    def __init__(self):
        from src.dummy_data import dummy_learning_content
        self._dummy_learning_content = dummy_learning_content

        # RAG services (always initialised — independent of USE_DUMMY_DATA)
        self.llm = get_llm()
        self.embeddings = get_embeddings()
        self.vector_store = get_vector_store()

        self._rag_available = (
            self.llm.is_available
            and self.embeddings.is_available
            and self.vector_store.is_available
        )

        if self._rag_available:
            logger.info("LearningPlatformAgent: Full RAG pipeline active (Groq + Gemini + Pinecone)")
        else:
            missing = []
            if not self.llm.is_available:
                missing.append("Groq LLM")
            if not self.embeddings.is_available:
                missing.append("Gemini Embeddings")
            if not self.vector_store.is_available:
                missing.append("Pinecone Vector Store")
            logger.warning(
                "LearningPlatformAgent: RAG fallback mode — missing: %s",
                ", ".join(missing),
            )

    # ── Public methods ───────────────────────────────────────────────────

    def recommend_content(
        self, farmer_id: str, topic: str | None = None, language: str = "hi-IN"
    ) -> List[LearningContent]:
        """Return personalised learning recommendations."""
        return self._dummy_learning_content(topic, language)

    def rag_answer(self, question: str) -> Dict[str, Any]:
        """
        Answer a question using the full RAG pipeline:
        1. Embed query with Gemini
        2. Search Pinecone for relevant chunks
        3. Generate answer with Groq LLM using retrieved context

        Falls back to local keyword matching if services are unavailable.
        """
        # Try full RAG pipeline first
        if self._rag_available:
            try:
                return self._rag_pipeline(question)
            except Exception as e:
                logger.warning("RAG pipeline failed, using local fallback: %s", e)

        # Fallback: local keyword-based matching
        return self._local_rag_fallback(question)

    # ── RAG Pipeline (Pinecone + Gemini + Groq) ─────────────────────────

    def _rag_pipeline(self, question: str) -> Dict[str, Any]:
        """Full RAG pipeline using real services."""
        # Step 1: Embed the query with Gemini
        query_embedding = self.embeddings.embed_query(question)

        # Step 2: Search Pinecone for top-k relevant chunks
        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=3,
            namespace="knowledge",
        )

        if not results:
            logger.info("No Pinecone results found, falling back to local RAG")
            return self._local_rag_fallback(question)

        # Step 3: Extract context chunks and sources
        context_chunks = [r["text"] for r in results]
        sources = [r["source"] for r in results]

        # Step 4: Generate answer using Groq LLM with retrieved context
        answer_result = self.llm.generate_rag_answer(
            question=question,
            context_chunks=context_chunks,
            sources=sources,
        )

        # Add retrieval metadata
        answer_result["retrieval_scores"] = [r["score"] for r in results]
        answer_result["topics"] = list(set(r.get("topic", "general") for r in results))
        answer_result["pipeline"] = "pinecone+gemini+groq"

        return answer_result

    # ── Local RAG Fallback ──────────────────────────────────────────────

    def _local_rag_fallback(self, question: str) -> Dict[str, Any]:
        """Simulated RAG using local keyword matching. Used when services are unavailable."""
        q_lower = question.lower()
        best_match = None
        best_score = 0

        for topic, entry in _RAG_KNOWLEDGE.items():
            keywords = topic.replace("_", " ").split() + entry["answer"][:100].lower().split()
            score = sum(1 for w in keywords if w in q_lower)
            if score > best_score:
                best_score = score
                best_match = (topic, entry)

        if best_match and best_score >= 1:
            topic, entry = best_match

            # If only LLM is available (but not embeddings/pinecone), use LLM to enhance
            if self.llm.is_available:
                try:
                    enhanced = self.llm.generate_rag_answer(
                        question=question,
                        context_chunks=[entry["answer"]],
                        sources=[entry["source"]],
                    )
                    enhanced["topic"] = topic
                    enhanced["pipeline"] = "local+groq"
                    return enhanced
                except Exception:
                    pass

            return {
                "answer": entry["answer"],
                "source": entry["source"],
                "sources": [entry["source"]],
                "topic": topic,
                "confidence": min(0.95, 0.5 + best_score * 0.08),
                "grounded": True,
                "pipeline": "local_fallback",
            }

        return {
            "answer": (
                "I don't have a specific answer for this question in my knowledge base. "
                "I recommend contacting your local KVK (Krishi Vigyan Kendra) for expert advice. "
                "You can also call the Kisan Call Centre at 1800-180-1551 (toll-free)."
            ),
            "source": "Fallback — escalation to human expert",
            "sources": [],
            "topic": "unknown",
            "confidence": 0.3,
            "grounded": False,
            "pipeline": "no_match",
        }

    # ── Agent interface (called by Supervisor) ───────────────────────────

    def handle_query(self, query: str, farmer_id: str, **ctx) -> AgentResponse:
        query_lower = query.lower()
        language = ctx.get("language", "hi-IN")

        # Learning content recommendation
        if any(w in query_lower for w in ["learn", "video", "course", "सीखना", "training", "content"]):
            topic = None
            for t in _RAG_KNOWLEDGE:
                if t.replace("_", " ") in query_lower:
                    topic = t
                    break
            contents = self.recommend_content(farmer_id, topic, language)
            lines = ["📚 Recommended learning content:"]
            for c in contents:
                lines.append(
                    f"  • [{c.content_type.upper()}] {c.title} "
                    f"({c.duration_minutes} min, relevance {c.relevance_score:.0%})"
                )
            return AgentResponse(
                agent_name=self.NAME,
                response_text="\n".join(lines),
                data={"content": [c.model_dump() for c in contents]},
                confidence=0.82,
            )

        # RAG Q&A (default path — uses Pinecone + Gemini + Groq)
        result = self.rag_answer(query)
        citations = result.get("sources", [])
        resp_text = result["answer"]

        if result.get("grounded", False) and citations:
            source_list = "; ".join(citations[:2])  # Show top 2 sources
            resp_text += f"\n\n📖 Sources: {source_list}"

        pipeline = result.get("pipeline", "unknown")
        logger.info("RAG answer via pipeline: %s", pipeline)

        return AgentResponse(
            agent_name=self.NAME,
            response_text=resp_text,
            data=result,
            confidence=result.get("confidence", 0.5),
            citations=citations,
        )
