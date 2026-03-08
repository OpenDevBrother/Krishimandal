"""
KrishiMandal — LLM Service (Groq)
Wraps the Groq API for chat completions using Llama 3.3-70B.
Used for agent response synthesis, RAG answer generation, and
intelligent query understanding.

This service is ALWAYS active regardless of USE_DUMMY_DATA.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.config import settings

logger = logging.getLogger(__name__)

# Singleton instance
_llm_instance: Optional["LLMService"] = None


class LLMService:
    """Groq-powered LLM service for the KrishiMandal platform."""

    def __init__(self):
        self._client = None
        self._available = False
        self._init_client()

    def _init_client(self):
        """Initialise the Groq client. Gracefully degrades if key is missing."""
        if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.startswith("gsk_your"):
            logger.warning(
                "GROQ_API_KEY not configured — LLM Service will use fallback mode. "
                "Set a valid key in .env to enable Groq LLM."
            )
            return
        try:
            from groq import Groq
            self._client = Groq(api_key=settings.GROQ_API_KEY)
            self._available = True
            logger.info("Groq LLM Service initialised (model=%s)", settings.GROQ_MODEL_ID)
        except ImportError:
            logger.warning("groq package not installed — run: pip install groq")
        except Exception as e:
            logger.warning("Failed to initialise Groq client: %s", e)

    @property
    def is_available(self) -> bool:
        return self._available

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Send a chat completion request to Groq.

        Args:
            messages: List of {"role": "user/assistant/system", "content": "..."}.
            temperature: Override default temperature.
            max_tokens: Override default max tokens.
            system_prompt: Convenience — prepended as a system message.

        Returns:
            The assistant's reply text, or a fallback string if unavailable.
        """
        if not self._available:
            return self._fallback_response(messages)

        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        try:
            response = self._client.chat.completions.create(
                model=settings.GROQ_MODEL_ID,
                messages=messages,
                temperature=temperature or settings.GROQ_TEMPERATURE,
                max_tokens=max_tokens or settings.GROQ_MAX_TOKENS,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Groq API call failed: %s", e, exc_info=True)
            return self._fallback_response(messages)

    def synthesise_agent_responses(
        self,
        query: str,
        agent_responses: List[Dict[str, Any]],
        language: str = "en",
    ) -> str:
        """
        Use the LLM to intelligently combine multiple agent responses
        into a single, coherent answer for the farmer.
        """
        agent_data = "\n\n".join(
            f"**{r['agent_name']}** (confidence {r.get('confidence', 'N/A')}):\n{r['response_text']}"
            for r in agent_responses
        )

        system_prompt = (
            "You are KrishiMandal, an AI farm intelligence assistant for Indian farmers. "
            "You are given a farmer's question and responses from multiple specialized agents. "
            "Synthesise them into a single, clear, actionable answer. "
            "Use simple language suitable for a farmer. Include specific numbers and recommendations. "
            "If the farmer's query is in Hindi or another Indian language, respond in the same language. "
            "Keep the answer concise — under 300 words."
        )

        user_message = (
            f"Farmer's question: {query}\n\n"
            f"Agent responses:\n{agent_data}\n\n"
            f"Provide a unified, helpful answer."
        )

        return self.chat(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=system_prompt,
        )

    def generate_rag_answer(
        self,
        question: str,
        context_chunks: List[str],
        sources: List[str],
    ) -> Dict[str, Any]:
        """
        Generate a grounded RAG answer using retrieved context from Pinecone.
        """
        context_text = "\n\n---\n\n".join(
            f"[Source {i+1}: {src}]\n{chunk}"
            for i, (chunk, src) in enumerate(zip(context_chunks, sources))
        )

        system_prompt = (
            "You are KrishiMandal, an expert agricultural AI advisor for Indian farmers. "
            "Answer the farmer's question using ONLY the provided context documents. "
            "If the context doesn't contain enough information, say so honestly and recommend "
            "contacting the local KVK (Krishi Vigyan Kendra) at 1800-180-1551. "
            "Always cite your sources. Keep answers practical and actionable. "
            "Respond in the same language as the question."
        )

        user_message = (
            f"Question: {question}\n\n"
            f"Context documents:\n{context_text}\n\n"
            f"Answer the question based on the above context."
        )

        answer = self.chat(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=system_prompt,
        )

        return {
            "answer": answer,
            "sources": sources,
            "grounded": True,
            "confidence": 0.85,
        }

    @staticmethod
    def _fallback_response(messages: List[Dict[str, str]]) -> str:
        """Return a simple fallback when LLM is not available."""
        last_content = messages[-1].get("content", "") if messages else ""
        return (
            f"[LLM unavailable — Groq API key not configured] "
            f"Received query: {last_content[:200]}... "
            f"Please set GROQ_API_KEY in .env for intelligent responses."
        )


def get_llm() -> LLMService:
    """Return the global LLM service singleton."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMService()
    return _llm_instance
