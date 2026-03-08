"""
KrishiMandal — RAG Knowledge Ingestion Script
Seeds the Pinecone vector store with agricultural knowledge documents
using Gemini embeddings.

Usage:
    python -m src.ingest_knowledge
"""
from __future__ import annotations

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-28s | %(levelname)-5s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Knowledge corpus ─────────────────────────────────────────────────────────
# Loaded from data/real_knowledge.json (curated ICAR, Vikaspedia, official sources).
# Falls back to a minimal built-in set if JSON file is missing.

def _load_knowledge_documents():
    """Load knowledge documents from real_knowledge.json or fallback to built-in."""
    import json
    from pathlib import Path

    json_path = Path(__file__).parent.parent / "data" / "real_knowledge.json"
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                docs = json.load(f)
            logger.info("Loaded %d knowledge documents from %s", len(docs), json_path)
            return docs
        except Exception as e:
            logger.warning("Failed to load real_knowledge.json: %s — using fallback", e)

    # Minimal fallback
    return [
        {
            "topic": "general",
            "source": "KrishiMandal — Default Knowledge",
            "text": "KrishiMandal is an AI platform for Indian farmers providing crop advisory, "
                    "price forecasts, scheme navigation, and supply chain optimization.",
        },
    ]


KNOWLEDGE_DOCUMENTS = _load_knowledge_documents()


def _chunk_text(text: str, max_tokens: int = 600) -> list[str]:
    """Split long text into chunks of ~max_tokens (approximated as words * 1.3)."""
    words = text.split()
    max_words = int(max_tokens / 1.3)
    if len(words) <= max_words:
        return [text]

    chunks = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i:i + max_words])
        if len(chunk.strip()) > 50:  # skip tiny fragments
            chunks.append(chunk)
    return chunks


def ingest_knowledge():
    """Embed and upsert all knowledge documents into Pinecone."""
    from src.config import settings
    from src.services.embeddings_service import get_embeddings
    from src.services.vector_store import get_vector_store

    embeddings_svc = get_embeddings()
    vector_store = get_vector_store()

    if not embeddings_svc.is_available:
        logger.error("❌ Gemini Embeddings not available. Set GEMINI_API_KEY in .env")
        sys.exit(1)

    if not vector_store.is_available:
        logger.error("❌ Pinecone Vector Store not available. Set PINECONE_API_KEY in .env")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  🌾 KrishiMandal — Knowledge Ingestion")
    print(f"  Documents: {len(KNOWLEDGE_DOCUMENTS)}")
    print(f"  Vector DB: Pinecone ({settings.PINECONE_INDEX_NAME})")
    print(f"  Embeddings: Gemini ({settings.GEMINI_EMBEDDING_MODEL})")
    print(f"{'='*60}\n")

    # Step 1: Chunk documents and generate embeddings
    print("📐 Chunking documents and generating Gemini embeddings...")
    texts = []
    metadatas = []
    for doc in KNOWLEDGE_DOCUMENTS:
        chunks = _chunk_text(doc["text"], max_tokens=600)
        for i, chunk in enumerate(chunks):
            texts.append(chunk)
            metadatas.append({
                "topic": doc["topic"],
                "source": doc["source"],
                "url": doc.get("url", ""),
                "language": doc.get("language", "en"),
                "chunk_index": i,
                "total_chunks": len(chunks),
            })

    print(f"   📄 {len(KNOWLEDGE_DOCUMENTS)} documents → {len(texts)} chunks")
    embeddings = embeddings_svc.embed_batch(texts, task_type="retrieval_document")
    print(f"   ✅ Generated {len(embeddings)} embeddings (dim={len(embeddings[0])})")

    # Step 3: Upsert into Pinecone
    print("📤 Upserting into Pinecone...")
    count = vector_store.upsert_documents(
        texts=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        namespace="knowledge",
    )
    print(f"   ✅ Upserted {count} vectors")

    # Step 4: Verify
    print("\n📊 Index stats:")
    stats = vector_store.get_index_stats()
    for k, v in stats.items():
        print(f"   {k}: {v}")

    # Step 5: Test search
    print("\n🔍 Test search: 'how to control pests in wheat'")
    query_emb = embeddings_svc.embed_query("how to control pests in wheat")
    results = vector_store.search(query_emb, top_k=3)
    for i, r in enumerate(results, 1):
        print(f"   {i}. [score={r['score']:.3f}] {r['source']}")
        print(f"      {r['text'][:120]}...")

    print(f"\n{'='*60}")
    print(f"  ✅ Knowledge ingestion complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    ingest_knowledge()
