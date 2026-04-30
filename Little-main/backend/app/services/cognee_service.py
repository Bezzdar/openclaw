from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _extract_text(item: Any) -> str:
    if isinstance(item, str):
        return item

    if not isinstance(item, dict):
        return ""

    for key in ("text", "content", "value", "answer", "description"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value

    return ""


def _extract_title(item: Any) -> str:
    if isinstance(item, dict):
        for key in ("title", "name", "source", "dataset_name"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return "Cognee"


def _extract_score(item: Any, default: float = 0.65) -> float:
    if isinstance(item, dict):
        for key in ("score", "relevance_score", "similarity"):
            value = item.get(key)
            if isinstance(value, (int, float)):
                return float(value)
    return default


class CogneeService:
    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if settings.cognee_api_token:
            headers["Authorization"] = f"Bearer {settings.cognee_api_token}"
        return headers

    async def search(self, query: str) -> list[dict]:
        if not settings.cognee_enabled:
            return []

        payload = {
            "query": query,
            "search_type": settings.cognee_search_type,
            "top_k": settings.rag_top_k,
        }
        if settings.cognee_default_dataset:
            payload["datasets"] = [settings.cognee_default_dataset]

        try:
            async with httpx.AsyncClient(timeout=settings.cognee_timeout_sec) as client:
                response = await client.post(
                    f"{settings.cognee_url.rstrip('/')}/api/v1/search",
                    json=payload,
                    headers=self._headers(),
                )
                response.raise_for_status()
                data = response.json()
        except Exception:
            logger.exception("Cognee search failed")
            return []

        if not isinstance(data, list):
            return []

        documents: list[dict] = []
        for item in data:
            content = _extract_text(item)
            if not content:
                continue
            score = _extract_score(item)
            documents.append(
                {
                    "content": content,
                    "title": _extract_title(item),
                    "score": score,
                    "source": "cognee",
                }
            )
            if len(documents) >= settings.rag_top_k:
                break

        return documents

    async def add_and_cognify(
        self,
        *,
        file_name: str,
        file_bytes: bytes,
        dataset_name: str,
        run_cognify: bool = True,
    ) -> dict:
        if not settings.cognee_enabled:
            return {
                "enabled": False,
                "dataset_name": dataset_name,
                "add_status": "skipped",
                "cognify_status": "skipped",
                "detail": "Cognee is disabled by configuration",
            }

        result = {
            "enabled": True,
            "dataset_name": dataset_name,
            "add_status": "failed",
            "cognify_status": "skipped",
            "detail": None,
        }

        auth_headers = {}
        if settings.cognee_api_token:
            auth_headers["Authorization"] = f"Bearer {settings.cognee_api_token}"

        try:
            async with httpx.AsyncClient(timeout=settings.cognee_timeout_sec) as client:
                add_response = await client.post(
                    f"{settings.cognee_url.rstrip('/')}/api/v1/add",
                    data={"datasetName": dataset_name},
                    files={"data": (file_name, file_bytes, "application/octet-stream")},
                    headers=auth_headers,
                )
                add_response.raise_for_status()
                result["add_status"] = "completed"

                if not run_cognify:
                    return result

                cognify_response = await client.post(
                    f"{settings.cognee_url.rstrip('/')}/api/v1/cognify",
                    json={"datasets": [dataset_name], "run_in_background": False},
                    headers=self._headers(),
                )
                cognify_response.raise_for_status()
                result["cognify_status"] = "completed"

                return result
        except Exception as error:
            logger.exception("Cognee add/cognify failed")
            result["detail"] = str(error)
            return result


cognee_service = CogneeService()
