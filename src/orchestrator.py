"""
KrishiMandal — Supervisor Orchestrator
Central intelligence that routes farmer queries to the right sub-agent(s),
handles multi-agent collaboration for complex queries, and synthesises
final responses using Groq LLM.

In production this maps to Amazon Bedrock's native Multi-Agent Collaboration
with Supervisor-with-Routing mode.  Locally it runs the same routing logic
in pure Python with Groq LLM for intelligent response synthesis.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.events import (
    HARVEST_PREDICTED,
    HEALTH_DECLINED,
    PEST_DETECTED,
    event_bus,
)
from src.agents.crop_management_agent import CropManagementAgent
from src.agents.digital_twin_agent import DigitalTwinAgent
from src.agents.learning_platform_agent import LearningPlatformAgent
from src.agents.price_predictor_agent import PricePredictorAgent
from src.agents.scheme_credit_agent import SchemeCreditAgent
from src.agents.supply_chain_agent import SupplyChainAgent
from src.config import settings
from src.models import AgentResponse, OrchestratorResult
from src.services.llm_service import get_llm

logger = logging.getLogger(__name__)


# ── Routing keywords per agent ───────────────────────────────────────────────
# The Supervisor uses these to decide which sub-agent(s) to invoke.
# When Groq LLM is available, it can also assist in routing complex queries.

_ROUTE_MAP: Dict[str, List[str]] = {
    "digital_twin": [
        "farm", "khet", "खेत", "profile", "weather", "mausam", "मौसम",
        "harvest", "katai", "काटना", "yield", "scenario", "simulate",
        "alert", "risk", "danger", "खतरा", "overview", "status",
        "inventory", "stock", "saman", "सामान", "beej", "बीज",
        "notification", "suchna", "सूचना", "unread",
    ],
    "crop_management": [
        "health", "crop", "fasal", "फसल", "pest", "keet", "कीट",
        "disease", "bimari", "बीमारी", "fertilizer", "khad", "खाद",
        "irrigation", "sinchai", "सिंचाई", "ndvi", "photo", "image",
        "urea", "dap", "input",
    ],
    "price_predictor": [
        "price", "bhav", "भाव", "rate", "mandi", "मंडी", "sell",
        "bechna", "बेचना", "store", "wait", "market", "cost",
        "income", "kamaayi", "कमाई", "realization",
    ],
    "scheme_credit": [
        "scheme", "yojana", "योजना", "subsidy", "government", "sarkari",
        "सरकारी", "credit", "loan", "rin", "ऋण", "bank", "document",
        "upload", "dastaawaiz", "दस्तावेज़", "pm-kisan", "pmfby",
        "kcc", "insurance",
        "apply", "application", "aavedan", "आवेदन",
    ],
    "supply_chain": [
        "logistics", "transport", "truck", "storage", "godam", "गोदाम",
        "route", "collection", "quality", "grade", "gunvatta", "गुणवत्ता",
        "buyer", "khariddar",
    ],
    "learning_platform": [
        "learn", "seekh", "सीखना", "video", "course", "training",
        "question", "organic", "drip", "soil", "water", "how to",
        "kaise", "कैसे", "tell me", "batao", "बताओ", "what is",
        "kya hai", "क्या है",
    ],
}


class SupervisorOrchestrator:
    """
    Central coordinator that mirrors Amazon Bedrock's
    Supervisor-with-Routing architecture locally,
    with Groq LLM for intelligent response synthesis.
    """

    def __init__(self):
        self.agents: Dict[str, Any] = {
            "digital_twin": DigitalTwinAgent(),
            "crop_management": CropManagementAgent(),
            "price_predictor": PricePredictorAgent(),
            "scheme_credit": SchemeCreditAgent(),
            "supply_chain": SupplyChainAgent(),
            "learning_platform": LearningPlatformAgent(),
        }
        self.llm = get_llm()
        self.event_bus = event_bus
        logger.info(
            "SupervisorOrchestrator initialised with %d sub-agents (LLM=%s)",
            len(self.agents),
            "Groq ✓" if self.llm.is_available else "fallback",
        )

    # ── Core routing ─────────────────────────────────────────────────────

    def route_query(
        self,
        query: str,
        farmer_id: str,
        language: str = "hi-IN",
        context: Optional[Dict[str, Any]] = None,
    ) -> OrchestratorResult:
        """
        Main entry point.  Classifies the query, routes to the
        appropriate sub-agent(s), and synthesises a response.
        """
        start = time.time()
        context = context or {}

        # Step 1 — Determine target agent(s)
        target_agents = self._classify_query(query)
        logger.info("Query routed to: %s", target_agents)

        # Step 2 — Invoke agent(s)
        agent_responses: List[AgentResponse] = []
        for agent_name in target_agents:
            agent = self.agents.get(agent_name)
            if agent is None:
                continue
            try:
                # Extract crop from farm profile for context
                if "crop" not in context:
                    dt = self.agents["digital_twin"]
                    profile = dt.get_farm_profile(farmer_id)
                    if profile.current_crops:
                        context["crop"] = profile.current_crops[0].crop_type
                resp = agent.handle_query(query, farmer_id, **context)
                agent_responses.append(resp)
            except Exception as e:
                logger.error("Agent %s failed: %s", agent_name, e, exc_info=True)
                agent_responses.append(
                    AgentResponse(
                        agent_name=agent_name,
                        response_text=f"Agent {agent_name} encountered an error.",
                        confidence=0.0,
                    )
                )

        # Step 3 — Synthesise final response (via Groq LLM if available)
        final_response = self._synthesise(query, agent_responses, language)

        # Step 4 — Fire cross-agent events
        self._check_and_fire_events(agent_responses, farmer_id)

        elapsed_ms = int((time.time() - start) * 1000)

        return OrchestratorResult(
            query=query,
            farmer_id=farmer_id,
            language=language,
            agents_invoked=target_agents,
            final_response=final_response,
            agent_responses=agent_responses,
            processing_time_ms=elapsed_ms,
        )

    # ── Classification ───────────────────────────────────────────────────

    def _classify_query(self, query: str) -> List[str]:
        """
        Determine which sub-agent(s) should handle the query.
        Simple queries → single agent (Routing mode).
        Complex queries → multiple agents (Supervisor mode).
        """
        query_lower = query.lower()
        scores: Dict[str, int] = {}

        for agent_name, keywords in _ROUTE_MAP.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                scores[agent_name] = score

        if not scores:
            # Default to learning_platform for general questions
            return ["learning_platform"]

        # Sort by score descending
        sorted_agents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_score = sorted_agents[0][1]

        # If top agent has a clear lead → routing mode (single agent)
        if len(sorted_agents) == 1 or sorted_agents[0][1] > sorted_agents[1][1] * 1.5:
            return [sorted_agents[0][0]]

        # Otherwise → supervisor mode (multi-agent, up to 3)
        multi = [name for name, s in sorted_agents if s >= top_score * 0.5]
        return multi[:3]

    # ── Response synthesis ───────────────────────────────────────────────

    def _synthesise(
        self,
        query: str,
        responses: List[AgentResponse],
        language: str = "en",
    ) -> str:
        """
        Combine responses from multiple agents into a unified answer.
        Uses Groq LLM for intelligent synthesis when available,
        falls back to template-based combining otherwise.
        """
        if not responses:
            return (
                "I'm sorry, I couldn't process your query. "
                "Please try rephrasing or contact your local KVK for help."
            )

        if len(responses) == 1:
            single = responses[0].response_text
            # Use LLM to polish single-agent responses too
            if self.llm.is_available:
                try:
                    polished = self.llm.chat(
                        messages=[{"role": "user", "content": f"Farmer asked: {query}\n\nAgent response: {single}\n\nPlease rewrite this response to be more natural, helpful, and farmer-friendly. Keep all factual information. Respond in the same language as the question."}],
                        system_prompt="You are KrishiMandal, a friendly AI farm advisor for Indian farmers. Rewrite agent responses to be warm, clear, and actionable. Keep it concise.",
                        max_tokens=512,
                    )
                    return polished
                except Exception as e:
                    logger.warning("LLM polish failed, using raw response: %s", e)
            return single

        # Multi-agent synthesis
        if self.llm.is_available:
            try:
                agent_data = [
                    {
                        "agent_name": r.agent_name,
                        "response_text": r.response_text,
                        "confidence": r.confidence,
                    }
                    for r in responses
                ]
                return self.llm.synthesise_agent_responses(query, agent_data, language)
            except Exception as e:
                logger.warning("LLM synthesis failed, using template: %s", e)

        # Fallback: template-based synthesis
        return self._template_synthesise(responses)

    def _template_synthesise(self, responses: List[AgentResponse]) -> str:
        """Template-based fallback when LLM is not available."""
        parts = []
        for r in responses:
            display_names = {
                "digital_twin": "🌾 Farm Status",
                "crop_management": "🌿 Crop Health",
                "price_predictor": "📈 Market Prices",
                "scheme_credit": "📋 Schemes & Credit",
                "supply_chain": "🚚 Supply Chain",
                "learning_platform": "📚 Knowledge",
            }
            name = display_names.get(r.agent_name, r.agent_name)
            parts.append(f"**{name}**:\n{r.response_text}")

        header = "Here's a comprehensive answer combining insights from multiple modules:\n\n"
        return header + "\n\n".join(parts)

    # ── Event firing ─────────────────────────────────────────────────────

    def _check_and_fire_events(
        self, responses: List[AgentResponse], farmer_id: str
    ):
        """Check agent responses and fire cross-agent events when appropriate."""
        for r in responses:
            # Harvest prediction → trigger supply chain + price forecast
            if r.agent_name == "digital_twin" and r.data.get("days_to_harvest", 999) <= 14:
                self.event_bus.publish(HARVEST_PREDICTED, {
                    "farmer_id": farmer_id,
                    "crop": r.data.get("crop", ""),
                    "days_to_harvest": r.data.get("days_to_harvest"),
                })

            # Pest detected → trigger learning content
            if r.agent_name == "crop_management" and "pest" in r.response_text.lower():
                self.event_bus.publish(PEST_DETECTED, {
                    "farmer_id": farmer_id,
                    "response": r.response_text[:200],
                })

            # Health declined
            if r.agent_name == "crop_management" and r.data.get("health_score", 100) < 60:
                self.event_bus.publish(HEALTH_DECLINED, {
                    "farmer_id": farmer_id,
                    "health_score": r.data.get("health_score"),
                })

    # ── Convenience ──────────────────────────────────────────────────────

    def list_agents(self) -> List[Dict[str, str]]:
        """Return a summary of all registered sub-agents."""
        descriptions = {
            "digital_twin": "Farm state, simulation, yield prediction, field boundaries",
            "crop_management": "Crop health, pest prediction, irrigation, fertilizer",
            "price_predictor": "Mandi prices, forecasts, sell/store decisions",
            "scheme_credit": "Government schemes, credit scoring, document OCR",
            "supply_chain": "Harvest logistics, market selection, transport, storage",
            "learning_platform": "Educational content, RAG chatbot, community Q&A",
        }
        return [
            {"name": name, "description": descriptions.get(name, "")}
            for name in self.agents
        ]
