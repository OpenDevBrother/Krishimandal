"""
KrishiMandal — Vector Store Service (Pinecone)
Manages the Pinecone index for RAG document storage and retrieval.
Handles index creation, document upsert, and similarity search.

This service is ALWAYS active regardless of USE_DUMMY_DATA.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.config import settings

logger = logging.getLogger(__name__)

# Singleton instance
_vector_store_instance: Optional["VectorStoreService"] = None


class VectorStoreService:
    """Pinecone-powered vector store for RAG knowledge management."""

    def __init__(self):
        self._index = None
        self._available = False
        self._init_client()

    def _init_client(self):
        """Initialise Pinecone client and ensure the index exists."""
        if not settings.PINECONE_API_KEY or settings.PINECONE_API_KEY.startswith("your_"):
            logger.warning(
                "PINECONE_API_KEY not configured — Vector Store will use fallback mode. "
                "Set a valid key in .env to enable Pinecone RAG."
            )
            return
        try:
            from pinecone import Pinecone, ServerlessSpec

            pc = Pinecone(api_key=settings.PINECONE_API_KEY)

            # Create index if it doesn't exist
            existing_indexes = [idx.name for idx in pc.list_indexes()]
            if settings.PINECONE_INDEX_NAME not in existing_indexes:
                logger.info(
                    "Creating Pinecone index '%s' (dim=%d, metric=%s)",
                    settings.PINECONE_INDEX_NAME,
                    settings.PINECONE_DIMENSION,
                    settings.PINECONE_METRIC,
                )
                pc.create_index(
                    name=settings.PINECONE_INDEX_NAME,
                    dimension=settings.PINECONE_DIMENSION,
                    metric=settings.PINECONE_METRIC,
                    spec=ServerlessSpec(
                        cloud=settings.PINECONE_CLOUD,
                        region=settings.PINECONE_ENVIRONMENT,
                    ),
                )

            self._index = pc.Index(settings.PINECONE_INDEX_NAME)
            self._available = True

            stats = self._index.describe_index_stats()
            logger.info(
                "Pinecone Vector Store initialised (index=%s, vectors=%d)",
                settings.PINECONE_INDEX_NAME,
                stats.get("total_vector_count", 0),
            )
        except ImportError:
            logger.warning("pinecone-client not installed — run: pip install pinecone-client")
        except Exception as e:
            logger.warning("Failed to initialise Pinecone: %s", e)

    @property
    def is_available(self) -> bool:
        return self._available

    def upsert_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        namespace: str = "knowledge",
    ) -> int:
        """
        Upsert documents into Pinecone.

        Args:
            texts: Raw text content of each document chunk.
            embeddings: Corresponding embedding vectors.
            metadatas: Optional metadata dicts for each document.
            namespace: Pinecone namespace for logical grouping.

        Returns:
            Number of vectors upserted.
        """
        if not self._available:
            logger.warning("Pinecone not available — skipping upsert")
            return 0

        vectors = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            doc_id = hashlib.md5(text.encode()).hexdigest()
            metadata = metadatas[i] if metadatas else {}
            metadata["text"] = text[:1000]  # Store text in metadata for retrieval
            vectors.append({
                "id": doc_id,
                "values": embedding,
                "metadata": metadata,
            })

        try:
            # Upsert in batches of 100
            batch_size = 100
            total = 0
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i : i + batch_size]
                self._index.upsert(vectors=batch, namespace=namespace)
                total += len(batch)

            logger.info("Upserted %d vectors into namespace '%s'", total, namespace)
            return total
        except Exception as e:
            logger.error("Pinecone upsert failed: %s", e, exc_info=True)
            return 0

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        namespace: str = "knowledge",
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents in Pinecone.

        Args:
            query_embedding: The query vector.
            top_k: Number of results to return.
            namespace: Pinecone namespace to search.
            filter_dict: Optional metadata filter.

        Returns:
            List of dicts with keys: id, score, text, metadata.
        """
        if not self._available:
            return []

        try:
            results = self._index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                namespace=namespace,
                filter=filter_dict,
            )

            matches = []
            for match in results.get("matches", []):
                metadata = match.get("metadata", {})
                matches.append({
                    "id": match["id"],
                    "score": match["score"],
                    "text": metadata.get("text", ""),
                    "source": metadata.get("source", "Unknown"),
                    "topic": metadata.get("topic", "general"),
                    "metadata": metadata,
                })

            logger.info(
                "Pinecone search returned %d results (top score=%.3f)",
                len(matches),
                matches[0]["score"] if matches else 0,
            )
            return matches
        except Exception as e:
            logger.error("Pinecone search failed: %s", e, exc_info=True)
            return []

    def get_index_stats(self) -> Dict[str, Any]:
        """Return index statistics."""
        if not self._available:
            return {"available": False}
        try:
            stats = self._index.describe_index_stats()
            return {
                "available": True,
                "index_name": settings.PINECONE_INDEX_NAME,
                "total_vectors": stats.get("total_vector_count", 0),
                "namespaces": {k: {"vector_count": v.get("vector_count", 0) if hasattr(v, "get") else getattr(v, "vector_count", 0)} for k, v in stats.get("namespaces", {}).items()},
                "dimension": stats.get("dimension", settings.PINECONE_DIMENSION),
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    def delete_namespace(self, namespace: str = "knowledge") -> bool:
        """Delete all vectors in a namespace."""
        if not self._available:
            return False
        try:
            self._index.delete(delete_all=True, namespace=namespace)
            logger.info("Deleted all vectors in namespace '%s'", namespace)
            return True
        except Exception as e:
            logger.error("Delete namespace failed: %s", e, exc_info=True)
            return False


def get_vector_store() -> VectorStoreService:
    """Return the global Vector Store service singleton."""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStoreService()
    return _vector_store_instance
