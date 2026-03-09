"""
KrishiMandal Serverless — RAG Lambda
Retrieval-Augmented Generation: S3 PDF → Titan Embeddings → Nova Pro answer.
Pipeline: Load PDF from S3 → chunk text → embed with Titan → cosine search → generate with Nova.
"""
import json
import logging
import math
import os
import re
from typing import Any, Dict, List, Tuple

import boto3

from common.bedrock_service import get_bedrock_llm
from common.config import config
from common.fallback import fallback_to_ec2
from common.response import ok, bad_request, error

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Cached knowledge base (persists across warm Lambda invocations)
_chunks: List[str] = []
_chunk_embeddings: List[List[float]] = []
_chunk_sources: List[str] = []
_loaded = False

S3_KNOWLEDGE_PREFIX = "knowledge/"


def _load_s3_documents() -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """Load knowledge from S3: JSON chunk files and PDFs.
    Returns (json_chunks, pdf_documents) where json_chunks are pre-chunked."""
    s3 = boto3.client("s3", region_name=config.AWS_REGION)
    bucket = config.S3_BUCKET

    try:
        resp = s3.list_objects_v2(Bucket=bucket, Prefix=S3_KNOWLEDGE_PREFIX)
        contents = resp.get("Contents", [])
    except Exception as e:
        logger.error("Failed to list S3 objects: %s", e)
        return [], []

    json_chunks = []  # (text, source) — already chunked
    pdf_documents = []  # (key, full_text) — need chunking

    for obj in contents:
        key = obj["Key"]
        try:
            if key.lower().endswith(".json"):
                # Pre-chunked JSON: [{text, source}, ...]
                resp_obj = s3.get_object(Bucket=bucket, Key=key)
                data = json.loads(resp_obj["Body"].read().decode())
                for item in data:
                    if item.get("text"):
                        json_chunks.append((item["text"], item.get("source", key)))
                logger.info("Loaded %d chunks from %s", len(data), key)

            elif key.lower().endswith(".pdf"):
                tmp_path = f"/tmp/{os.path.basename(key)}"
                s3.download_file(bucket, key, tmp_path)
                text = _extract_pdf_text(tmp_path)
                if text.strip():
                    pdf_documents.append((key, text))
                    logger.info("Loaded PDF %s (%d chars)", key, len(text))

        except Exception as e:
            logger.warning("Failed to process %s: %s", key, e)

    return json_chunks, pdf_documents


def _extract_pdf_text(pdf_path: str) -> str:
    """Extract text from PDF using basic binary parsing (no external libs)."""
    try:
        with open(pdf_path, "rb") as f:
            data = f.read()

        # Extract text between BT/ET blocks and decode parenthesized strings
        text_parts = []
        # Find all string literals in PDF content streams
        i = 0
        raw = data.decode("latin-1", errors="ignore")

        # Method 1: Extract parenthesized text strings (Tj/TJ operators)
        for match in re.finditer(r'\(([^)]*)\)', raw):
            part = match.group(1)
            # Unescape PDF string escapes
            part = part.replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t")
            part = re.sub(r'\\([0-7]{1,3})', lambda m: chr(int(m.group(1), 8)), part)
            part = part.replace("\\(", "(").replace("\\)", ")").replace("\\\\", "\\")
            cleaned = part.strip()
            if cleaned and len(cleaned) > 1:
                text_parts.append(cleaned)

        if text_parts:
            return "\n".join(text_parts)

        # Fallback: just get printable ASCII sequences
        printable = re.findall(r'[A-Za-z][A-Za-z0-9 ,.\-:;!?\'\"]{10,}', raw)
        return "\n".join(printable)

    except Exception as e:
        logger.warning("PDF text extraction failed: %s", e)
        return ""


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks by sentences."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) > chunk_size and current:
            chunks.append(current.strip())
            # Keep overlap from end of current chunk
            words = current.split()
            overlap_words = words[-overlap // 5:] if len(words) > overlap // 5 else words
            current = " ".join(overlap_words) + " " + sentence
        else:
            current = (current + " " + sentence).strip()

    if current.strip():
        chunks.append(current.strip())

    return [c for c in chunks if len(c) > 30]


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _load_knowledge_base():
    """Load knowledge from S3 + built-in, embed all chunks. Cached across warm invocations."""
    global _chunks, _chunk_embeddings, _chunk_sources, _loaded
    if _loaded:
        return

    llm = get_bedrock_llm()

    # Load from S3 (JSON pre-chunked files + PDFs)
    json_chunks, pdf_documents = _load_s3_documents()

    # Add pre-chunked JSON entries
    for text, source in json_chunks:
        embedding = llm.embed_text(text)
        if embedding:
            _chunks.append(text)
            _chunk_embeddings.append(embedding)
            _chunk_sources.append(source)

    # Add PDF documents (chunk them first)
    for doc_key, text in pdf_documents:
        doc_chunks = _chunk_text(text)
        for chunk in doc_chunks:
            embedding = llm.embed_text(chunk)
            if embedding:
                _chunks.append(chunk)
                _chunk_embeddings.append(embedding)
                _chunk_sources.append(doc_key)

    logger.info("S3 knowledge loaded: %d chunks (%d json, %d pdf docs)", len(_chunks), len(json_chunks), len(pdf_documents))

    # Add built-in Indian agriculture knowledge
    for topic, entry in _INDIAN_AG_KNOWLEDGE.items():
        embedding = llm.embed_text(entry["answer"])
        if embedding:
            _chunks.append(entry["answer"])
            _chunk_embeddings.append(embedding)
            _chunk_sources.append(entry["source"])

    logger.info("Total knowledge base: %d chunks", len(_chunks))
    _loaded = True


def _search_similar(query_embedding: List[float], top_k: int = 3) -> List[Tuple[str, str, float]]:
    """Find top-k most similar chunks."""
    if not _chunk_embeddings:
        return []

    scores = []
    for i, emb in enumerate(_chunk_embeddings):
        sim = _cosine_similarity(query_embedding, emb)
        scores.append((sim, i))

    scores.sort(reverse=True)
    results = []
    for sim, idx in scores[:top_k]:
        if sim > 0.3:  # minimum similarity threshold
            results.append((_chunks[idx], _chunk_sources[idx], sim))

    return results


# Built-in Indian agriculture knowledge (supplements PDF content)
_INDIAN_AG_KNOWLEDGE: Dict[str, Dict[str, str]] = {
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
            "Rainwater harvesting: Build farm ponds (30x30x3m captures ~27 lakh litres). "
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
            "PM-KISAN provides Rs 6,000/year in 3 instalments of Rs 2,000 directly to bank account. "
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


def handler(event, context):
    """Lambda handler for POST /rag/ask."""
    try:
        method = event.get("httpMethod", "POST")
        if method != "POST":
            return bad_request("Only POST is supported.")

        body = json.loads(event.get("body", "{}"))
        question = body.get("query", "").strip()
        if not question:
            return bad_request("query is required.")

        farmer_id = body.get("farmer_id", "")
        language = body.get("language", "en")

        llm = get_bedrock_llm()

        # Load and embed knowledge base (cached after first call)
        _load_knowledge_base()

        # Embed the question
        query_embedding = llm.embed_text(question)

        if query_embedding and _chunk_embeddings:
            # Vector search
            matches = _search_similar(query_embedding, top_k=3)

            if matches:
                chunks = [m[0] for m in matches]
                sources = [m[1] for m in matches]
                scores = [m[2] for m in matches]

                result = llm.generate_rag_answer(
                    question=question,
                    context_chunks=chunks,
                    sources=sources,
                )
                result["retrieval_scores"] = scores
                result["pipeline"] = "s3_titan_nova"
                result["num_chunks_searched"] = len(_chunks)
                return ok(result)

        # Fallback: keyword matching against built-in knowledge
        result = _keyword_fallback(question, llm)
        return ok(result)

    except Exception as e:
        logger.error("RAG handler failed: %s", e, exc_info=True)
        fb = fallback_to_ec2(
            method="POST",
            path="/rag/ask",
            body=json.loads(event.get("body", "{}")) if event.get("body") else None,
        )
        return fb or error(str(e))


def _keyword_fallback(question: str, llm) -> Dict[str, Any]:
    """Keyword-based fallback when embeddings aren't available."""
    q_lower = question.lower()
    best_match = None
    best_score = 0

    for topic, entry in _INDIAN_AG_KNOWLEDGE.items():
        keywords = topic.replace("_", " ").split() + entry["answer"][:100].lower().split()
        score = sum(1 for w in keywords if w in q_lower)
        if score > best_score:
            best_score = score
            best_match = (topic, entry)

    if best_match and best_score >= 1:
        topic, entry = best_match
        try:
            enhanced = llm.generate_rag_answer(
                question=question,
                context_chunks=[entry["answer"]],
                sources=[entry["source"]],
            )
            enhanced["topic"] = topic
            enhanced["pipeline"] = "keyword+nova"
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
            "pipeline": "keyword_fallback",
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
