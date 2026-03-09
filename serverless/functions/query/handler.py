"""
KrishiMandal Serverless — Query Lambda
Multi-agent orchestrator: routes farmer queries to sub-agents,
synthesises responses using Bedrock Claude.
"""
import json
import logging
import time
from typing import Any, Dict, List, Optional

from common.bedrock_service import get_bedrock_llm
from common.dynamo_repository import get_repository
from common.twilio_whatsapp import send_whatsapp, is_configured as twilio_configured
from common.fallback import fallback_to_ec2
from common.response import ok, bad_request, error

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ── Routing keywords per agent ───────────────────────────────────────────
ROUTE_MAP: Dict[str, List[str]] = {
    "digital_twin": [
        "farm", "khet", "खेत", "profile", "weather", "mausam", "मौसम",
        "harvest", "katai", "काटना", "yield", "scenario", "simulate",
        "alert", "risk", "danger", "खतरा", "overview", "status",
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
        "upload", "दस्तावेज़", "pm-kisan", "pmfby", "kcc", "insurance",
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

AGENT_DESCRIPTIONS = {
    "digital_twin": "Farm state, simulation, yield prediction, field boundaries",
    "crop_management": "Crop health, pest prediction, irrigation, fertilizer",
    "price_predictor": "Mandi prices, forecasts, sell/store decisions",
    "scheme_credit": "Government schemes, credit scoring, document OCR",
    "supply_chain": "Harvest logistics, market selection, transport, storage",
    "learning_platform": "Educational content, RAG chatbot, community Q&A",
}


def classify_query(query: str) -> List[str]:
    """Determine which sub-agent(s) should handle the query."""
    query_lower = query.lower()
    scores: Dict[str, int] = {}
    for agent_name, keywords in ROUTE_MAP.items():
        score = sum(1 for kw in keywords if kw in query_lower)
        if score > 0:
            scores[agent_name] = score

    if not scores:
        return ["learning_platform"]

    sorted_agents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_agents) == 1 or sorted_agents[0][1] > sorted_agents[1][1] * 1.5:
        return [sorted_agents[0][0]]

    top_score = sorted_agents[0][1]
    multi = [name for name, s in sorted_agents if s >= top_score * 0.5]
    return multi[:3]


def _agent_handle_query(agent_name: str, query: str, farmer_id: str) -> Dict:
    """Invoke a sub-agent using Bedrock LLM."""
    llm = get_bedrock_llm()
    repo = get_repository()

    # Build context from DynamoDB
    farm = repo.get_farm(farmer_id)
    farm_context = ""
    if farm:
        crop = farm.get("current_crop", "wheat")
        farm_context = (
            f"Farmer: {farm.get('farmer_name', farmer_id)}, "
            f"Area: {farm.get('area_hectares', 'N/A')} hectares, "
            f"Crop: {crop}, Soil: {farm.get('soil_type', 'N/A')}, "
            f"Irrigation: {farm.get('irrigation_type', 'N/A')}"
        )

    system_prompts = {
        "digital_twin": "You are a digital twin agent for Indian farms. Provide farm status, weather insights, yield predictions, and risk alerts.",
        "crop_management": "You are a crop management expert. Provide health assessments, pest predictions, fertilizer and irrigation recommendations.",
        "price_predictor": "You are a mandi price analyst. Provide price forecasts, sell/store recommendations, and market insights for Indian agricultural commodities.",
        "scheme_credit": "You are an expert on Indian government agricultural schemes and credit. Help farmers find eligible schemes, compute credit scores, and navigate applications.",
        "supply_chain": "You are a supply chain optimizer. Provide harvest planning, market selection, transport logistics, and quality grading advice.",
        "learning_platform": "You are an agricultural knowledge expert. Answer farming questions, provide learning recommendations, and share best practices for Indian agriculture.",
    }

    prompt = f"Farmer's question: {query}"
    if farm_context:
        prompt = f"Farm context: {farm_context}\n\n{prompt}"

    response_text = llm.chat(
        messages=[{"role": "user", "content": prompt}],
        system_prompt=system_prompts.get(agent_name, "You are a helpful agricultural AI assistant."),
        max_tokens=1024,
    )

    return {
        "agent_name": agent_name,
        "response_text": response_text,
        "confidence": 0.85,
    }


def handler(event, context):
    """Lambda handler for /query and /agents endpoints."""
    try:
        method = event.get("httpMethod", "GET")
        path = event.get("path", "")

        # GET /agents
        if method == "GET" and path.endswith("/agents"):
            agents_list = [
                {"name": name, "description": desc}
                for name, desc in AGENT_DESCRIPTIONS.items()
            ]
            return ok(agents_list)

        # POST /query
        if method == "POST":
            body = json.loads(event.get("body", "{}"))
            query = body.get("query", "")
            farmer_id = body.get("farmer_id", "F1001")
            language = body.get("language", "hi-IN")

            if not query:
                return bad_request("Query is required.")

            start = time.time()

            # Route to agents
            target_agents = classify_query(query)
            logger.info("Query routed to: %s", target_agents)

            # Invoke agents
            agent_responses = []
            for agent_name in target_agents:
                try:
                    resp = _agent_handle_query(agent_name, query, farmer_id)
                    agent_responses.append(resp)
                except Exception as e:
                    logger.error("Agent %s failed: %s", agent_name, e)
                    agent_responses.append({
                        "agent_name": agent_name,
                        "response_text": f"Agent {agent_name} encountered an error.",
                        "confidence": 0.0,
                    })

            # Synthesise response
            llm = get_bedrock_llm()
            if len(agent_responses) == 1:
                final_response = agent_responses[0]["response_text"]
            else:
                final_response = llm.synthesise_agent_responses(
                    query, agent_responses, language
                )

            elapsed_ms = int((time.time() - start) * 1000)

            # ── WhatsApp send tool ──
            # If user asked to send via WhatsApp, do it
            whatsapp_sent = False
            query_lower = query.lower()
            whatsapp_triggers = [
                "send me a whatsapp", "send whatsapp", "whatsapp bhejo",
                "whatsapp par bhejo", "send on whatsapp", "whatsapp me",
                "whatsapp mujhe", "message me on whatsapp", "whatsapp send",
            ]
            if any(t in query_lower for t in whatsapp_triggers) and twilio_configured():
                repo = get_repository()
                farm = repo.get_farm(farmer_id)
                if farm and farm.get("whatsapp_enabled") and farm.get("phone"):
                    phone = farm["phone"]
                    if not phone.startswith("+"):
                        phone = f"+91{phone}" if not phone.startswith("91") else f"+{phone}"
                    # Strip markdown for WhatsApp
                    wa_text = final_response.replace("**", "*").replace("##", "").replace("# ", "")
                    if len(wa_text) > 1600:
                        wa_text = wa_text[:1597] + "..."
                    wa_msg = f"🤖 *KrishiMandal AI*\n\n{wa_text}"
                    result = send_whatsapp(phone, wa_msg)
                    whatsapp_sent = result.get("success", False)
                    if whatsapp_sent:
                        final_response += "\n\n✅ _Response also sent to your WhatsApp._"
                    else:
                        final_response += "\n\n⚠️ _Could not send WhatsApp. Make sure you have joined the Twilio sandbox and enabled WhatsApp in your profile._"

            return ok({
                "query": query,
                "farmer_id": farmer_id,
                "language": language,
                "agents_invoked": target_agents,
                "final_response": final_response,
                "processing_time_ms": elapsed_ms,
                "whatsapp_sent": whatsapp_sent,
            })

        return bad_request("Unsupported method.")

    except Exception as e:
        logger.error("Query handler failed: %s", e, exc_info=True)
        # Fallback to EC2
        fb = fallback_to_ec2(
            method=event.get("httpMethod", "POST"),
            path=event.get("path", "/query"),
            body=json.loads(event.get("body", "{}")) if event.get("body") else None,
        )
        return fb or error(f"Query processing failed: {str(e)}")
