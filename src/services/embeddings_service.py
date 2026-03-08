"""
KrishiMandal — Embeddings Service (Google Gemini)
Generates text embeddings using Google's text-embedding-004 model.
Used for encoding RAG documents and queries before Pinecone storage/retrieval.

This service is ALWAYS active regardless of USE_DUMMY_DATA.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from src.config import settings

logger = logging.getLogger(__name__)

# Singleton instance
_embeddings_instance: Optional["EmbeddingsService"] = None


class EmbeddingsService:
    """Google Gemini-powered embedding service."""

    def __init__(self):
        self._client = None
        self._available = False
        self._init_client()

    def _init_client(self):
        """Initialise the Gemini client. Gracefully degrades if key is missing."""
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.startswith("your_"):
            logger.warning(
                "GEMINI_API_KEY not configured — Embeddings Service will use fallback mode. "
                "Set a valid key in .env to enable Gemini embeddings."
            )
            return
        try:
            from google import genai
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            self._available = True
            logger.info(
                "Gemini Embeddings Service initialised (model=%s)",
                settings.GEMINI_EMBEDDING_MODEL,
            )
        except ImportError:
            logger.warning("google-genai package not installed — run: pip install google-genai")
        except Exception as e:
            logger.warning("Failed to initialise Gemini client: %s", e)

    @property
    def is_available(self) -> bool:
        return self._available

    def embed_text(self, text: str) -> List[float]:
        """
        Generate an embedding vector for a single text string.

        Returns:
            A list of floats (dimension depends on model, text-embedding-004 = 768).
        """
        if not self._available:
            return self._fallback_embedding()

        try:
            from google.genai import types
            result = self._client.models.embed_content(
                model=settings.GEMINI_EMBEDDING_MODEL,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type="retrieval_document",
                    output_dimensionality=settings.PINECONE_DIMENSION
                ),
            )
            return result.embeddings[0].values
        except Exception as e:
            logger.error("Gemini embedding failed: %s", e, exc_info=True)
            return self._fallback_embedding()

    def embed_query(self, query: str) -> List[float]:
        """
        Generate an embedding vector optimised for query retrieval.
        """
        if not self._available:
            return self._fallback_embedding()

        try:
            from google.genai import types
            result = self._client.models.embed_content(
                model=settings.GEMINI_EMBEDDING_MODEL,
                contents=query,
                config=types.EmbedContentConfig(
                    task_type="retrieval_query",
                    output_dimensionality=settings.PINECONE_DIMENSION
                ),
            )
            return result.embeddings[0].values
        except Exception as e:
            logger.error("Gemini query embedding failed: %s", e, exc_info=True)
            return self._fallback_embedding()

    def embed_batch(self, texts: List[str], task_type: str = "retrieval_document") -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a single batch.
        """
        if not self._available:
            return [self._fallback_embedding() for _ in texts]

        try:
            from google.genai import types
            # Using loop for batch since google.genai interface changed
            results = []
            for text in texts:
                result = self._client.models.embed_content(
                    model=settings.GEMINI_EMBEDDING_MODEL,
                    contents=text,
                    config=types.EmbedContentConfig(
                        task_type=task_type,
                        output_dimensionality=settings.PINECONE_DIMENSION
                    ),
                )
                results.append(result.embeddings[0].values)
            return results
        except Exception as e:
            logger.error("Gemini batch embedding failed: %s", e, exc_info=True)
            return [self._fallback_embedding() for _ in texts]

    @staticmethod
    def _fallback_embedding() -> List[float]:
        """Return a zero vector as fallback when embeddings are unavailable."""
        return [0.0] * settings.PINECONE_DIMENSION


def get_embeddings() -> EmbeddingsService:
    """Return the global Embeddings service singleton."""
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = EmbeddingsService()
    return _embeddings_instance
