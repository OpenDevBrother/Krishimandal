"""
KrishiMandal Serverless — Bedrock LLM Service
Supports Amazon Nova and Anthropic Claude models.
"""
import json
import logging
from typing import Any, Dict, List, Optional

import boto3

from common.config import config

logger = logging.getLogger(__name__)

_instance: Optional["BedrockLLMService"] = None


class BedrockLLMService:
    """Amazon Bedrock LLM service supporting Nova and Claude models."""

    def __init__(self):
        self._client = boto3.client("bedrock-runtime", region_name=config.AWS_REGION)
        self._model_id = config.BEDROCK_MODEL_ID
        self._embedding_client = boto3.client("bedrock-runtime", region_name=config.AWS_REGION)
        self._is_nova = "nova" in self._model_id.lower()
        logger.info("Bedrock LLM Service initialized (model=%s, nova=%s)", self._model_id, self._is_nova)

    def _build_nova_body(self, messages, system_prompt, max_tokens, temperature):
        """Build request body for Amazon Nova models."""
        nova_messages = []
        for msg in messages:
            role = msg["role"]
            if role == "system":
                if not system_prompt:
                    system_prompt = msg["content"]
                continue
            nova_messages.append({
                "role": role,
                "content": [{"text": msg["content"]}],
            })
        body = {
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
            "messages": nova_messages,
        }
        if system_prompt:
            body["system"] = [{"text": system_prompt}]
        return body

    def _build_anthropic_body(self, messages, system_prompt, max_tokens, temperature):
        """Build request body for Anthropic Claude models."""
        bedrock_messages = []
        for msg in messages:
            role = msg["role"]
            if role == "system":
                if not system_prompt:
                    system_prompt = msg["content"]
                continue
            bedrock_messages.append({
                "role": role,
                "content": [{"type": "text", "text": msg["content"]}],
            })
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": bedrock_messages,
        }
        if system_prompt:
            body["system"] = system_prompt
        return body

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Send a chat completion request to Bedrock."""
        try:
            if self._is_nova:
                body = self._build_nova_body(messages, system_prompt, max_tokens, temperature)
            else:
                body = self._build_anthropic_body(messages, system_prompt, max_tokens, temperature)

            kwargs = {
                "modelId": self._model_id,
                "body": json.dumps(body),
                "contentType": "application/json",
                "accept": "application/json",
            }
            if not self._is_nova and config.BEDROCK_GUARDRAIL_ID:
                kwargs["guardrailIdentifier"] = config.BEDROCK_GUARDRAIL_ID
                kwargs["guardrailVersion"] = "DRAFT"

            response = self._client.invoke_model(**kwargs)
            result = json.loads(response["body"].read())

            if self._is_nova:
                return result["output"]["message"]["content"][0]["text"].strip()
            return result["content"][0]["text"].strip()

        except Exception as e:
            logger.error("Bedrock API call failed: %s", e, exc_info=True)
            return self._fallback_response(messages)

    def embed_text(self, text: str) -> List[float]:
        """Generate embeddings using Bedrock Titan Embeddings."""
        try:
            body = json.dumps({
                "inputText": text,
            })
            response = self._embedding_client.invoke_model(
                modelId=config.BEDROCK_EMBEDDING_MODEL_ID,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            result = json.loads(response["body"].read())
            return result["embedding"]
        except Exception as e:
            logger.error("Bedrock embedding failed: %s", e)
            return []

    def synthesise_agent_responses(
        self,
        query: str,
        agent_responses: List[Dict[str, Any]],
        language: str = "en",
    ) -> str:
        """Combine multiple agent responses into a single answer."""
        agent_data = "\n\n".join(
            f"**{r['agent_name']}** (confidence {r.get('confidence', 'N/A')}):\n{r['response_text']}"
            for r in agent_responses
        )
        system_prompt = (
            "You are KrishiMandal, an AI farm intelligence assistant for Indian farmers. "
            "Synthesise the agent responses into a single, clear, actionable answer. "
            "Use simple language. Include specific numbers and recommendations. "
            "If the query is in Hindi or another Indian language, respond in the same language. "
            "Keep the answer concise — under 300 words."
        )
        return self.chat(
            messages=[{"role": "user", "content": f"Farmer's question: {query}\n\nAgent responses:\n{agent_data}\n\nProvide a unified, helpful answer."}],
            system_prompt=system_prompt,
        )

    def generate_rag_answer(
        self,
        question: str,
        context_chunks: List[str],
        sources: List[str],
    ) -> Dict[str, Any]:
        """Generate a grounded RAG answer."""
        context_text = "\n\n---\n\n".join(
            f"[Source {i+1}: {src}]\n{chunk}"
            for i, (chunk, src) in enumerate(zip(context_chunks, sources))
        )
        system_prompt = (
            "You are KrishiMandal, an expert agricultural AI advisor. "
            "Answer using ONLY the provided context. Cite sources. "
            "If insufficient info, recommend contacting KVK at 1800-180-1551. "
            "Respond in the same language as the question."
        )
        answer = self.chat(
            messages=[{"role": "user", "content": f"Question: {question}\n\nContext:\n{context_text}\n\nAnswer based on context."}],
            system_prompt=system_prompt,
        )
        return {"answer": answer, "sources": sources, "grounded": True, "confidence": 0.85}

    @staticmethod
    def _fallback_response(messages: List[Dict[str, str]]) -> str:
        last_content = messages[-1].get("content", "") if messages else ""
        return f"[Bedrock unavailable] Received: {last_content[:200]}..."


def get_bedrock_llm() -> BedrockLLMService:
    global _instance
    if _instance is None:
        _instance = BedrockLLMService()
    return _instance
