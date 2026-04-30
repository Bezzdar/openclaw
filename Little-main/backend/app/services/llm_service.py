import json
from collections.abc import AsyncGenerator

import httpx

from app.config import settings
from app.models.schemas import ChatMessage

SYSTEM_PROMPT = (
    "You are a corporate AI assistant. Reply in Russian, clearly and concisely. "
    "If knowledge-base context is provided, prioritize it and do not invent facts outside it. "
    "If context is empty or insufficient, still provide a useful best-effort answer from general knowledge. "
    "Do not say that you cannot answer only because context is missing."
)


class LLMService:
    """Handles interaction with Ollama LLM, including streaming."""

    async def generate_stream(
        self,
        user_message: str,
        rag_context: str,
        history: list[ChatMessage],
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens from Ollama."""
        messages = self._build_messages(user_message, rag_context, history)

        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            async with client.stream(
                "POST",
                f"{settings.ollama_url}/api/chat",
                json={
                    "model": settings.ollama_model,
                    "messages": messages,
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    if chunk.get("done"):
                        break
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token

    def _build_messages(
        self,
        user_message: str,
        rag_context: str,
        history: list[ChatMessage],
    ) -> list[dict]:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})

        if rag_context:
            augmented = (
                f"Knowledge-base context:\n\n{rag_context}\n\n"
                f"User question: {user_message}"
            )
        else:
            augmented = user_message

        messages.append({"role": "user", "content": augmented})
        return messages


llm_service = LLMService()
