import httpx
from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime

from config import settings
from models import LLMResponse, VectorSearchResult

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.api_base = settings.openai_api_base or "https://api.openai.com/v1"
        self.model_name = settings.model_name
        self.api_key = settings.openai_api_key

    async def health_check(self) -> str:
        """Check if LLM service is healthy"""
        try:
            # Simple health check - try to make a minimal request
            if not self.api_key:
                return "no_api_key"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # Try to list models as a health check
            response = await self.client.get(
                f"{self.api_base}/models",
                headers=headers
            )

            if response.status_code == 200:
                return "connected"
            else:
                return "error"

        except Exception as e:
            logger.error(f"LLM service health check failed: {e}")
            return "disconnected"

    async def generate_response(
        self,
        query: str,
        context_chunks: List[VectorSearchResult],
        domain: str = "general",
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> LLMResponse:
        """Generate response using LLM with RAG context"""
        try:
            # Build context from retrieved chunks
            context = self._build_context(context_chunks, domain)

            # Create system prompt based on domain
            system_prompt = self._get_system_prompt(domain)

            # Build messages
            messages = [{"role": "system", "content": system_prompt}]

            # Add chat history if provided
            if chat_history:
                messages.extend(chat_history[-10:])  # Last 10 messages for context

            # Add current user message with context
            user_message = self._format_user_message(query, context)
            messages.append({"role": "user", "content": user_message})

            # Make API call
            response = await self._call_llm_api(messages)

            return LLMResponse(
                content=response["content"],
                usage=response.get("usage"),
                model=self.model_name,
                sources=context_chunks
            )

        except Exception as e:
            logger.error(f"Failed to generate LLM response: {e}")
            # Return fallback response
            return LLMResponse(
                content="죄송합니다. 현재 응답을 생성할 수 없습니다. 잠시 후 다시 시도해주세요.",
                model=self.model_name,
                sources=context_chunks
            )

    async def _call_llm_api(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Make API call to LLM service"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1500,
            "top_p": 0.9
        }

        response = await self.client.post(
            f"{self.api_base}/chat/completions",
            headers=headers,
            json=payload
        )

        if response.status_code != 200:
            error_text = response.text
            raise Exception(f"LLM API error {response.status_code}: {error_text}")

        result = response.json()

        return {
            "content": result["choices"][0]["message"]["content"],
            "usage": result.get("usage", {})
        }

    def _build_context(self, context_chunks: List[VectorSearchResult], domain: str) -> str:
        """Build context string from retrieved chunks"""
        if not context_chunks:
            return "관련 문서를 찾을 수 없습니다."

        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            context_parts.append(
                f"[문서 {i}: {chunk.document_name}]\n{chunk.chunk_text}\n"
            )

        return "\n".join(context_parts)

    def _get_system_prompt(self, domain: str) -> str:
        """Get domain-specific system prompt"""
        base_prompt = """당신은 전문 문서 분석 어시스턴트입니다. 제공된 문서 내용을 바탕으로 정확하고 유용한 답변을 제공해주세요.

다음 원칙을 따라주세요:
1. 제공된 문서 내용만을 바탕으로 답변하세요
2. 확실하지 않은 내용은 추측하지 마세요
3. 답변 시 어떤 문서를 참조했는지 명시해주세요
4. 전문적이면서도 이해하기 쉽게 설명해주세요
5. 한국어로 답변해주세요"""

        domain_prompts = {
            "legal": base_prompt + "\n\n법률 문서 분석 시 조항, 판례, 법적 근거를 명확히 제시해주세요.",
            "medical": base_prompt + "\n\n의료 문서 분석 시 의학적 정확성을 중시하고, 전문 용어는 쉽게 설명해주세요.",
            "financial": base_prompt + "\n\n금융 문서 분석 시 수치, 지표, 리스크 요인을 명확히 제시해주세요.",
            "technical": base_prompt + "\n\n기술 문서 분석 시 기술적 세부사항과 구현 방법을 구체적으로 설명해주세요.",
        }

        return domain_prompts.get(domain, base_prompt)

    def _format_user_message(self, query: str, context: str) -> str:
        """Format user message with context"""
        return f"""다음 문서들을 참고하여 질문에 답해주세요:

=== 참고 문서 ===
{context}

=== 질문 ===
{query}

위 문서들을 바탕으로 정확하고 자세한 답변을 제공해주세요."""

    async def summarize_document(self, text: str, domain: str = "general") -> str:
        """Generate document summary"""
        try:
            system_prompt = f"""당신은 문서 요약 전문가입니다.
다음 {domain} 분야 문서의 핵심 내용을 3-5개 포인트로 요약해주세요:
1. 문서의 주요 목적
2. 핵심 내용
3. 중요한 세부사항
4. 결론 또는 권고사항

한국어로 명확하고 간결하게 요약해주세요."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"다음 문서를 요약해주세요:\n\n{text[:3000]}"}  # Limit text length
            ]

            response = await self._call_llm_api(messages)
            return response["content"]

        except Exception as e:
            logger.error(f"Failed to summarize document: {e}")
            return "문서 요약을 생성할 수 없습니다."

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()