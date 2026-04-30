import asyncio

import httpx
from elasticsearch import AsyncElasticsearch

from app.config import settings
from app.services.cognee_service import cognee_service


class RAGService:
    """Handles retrieval from Elasticsearch indices and optional Cognee search."""

    def __init__(self) -> None:
        self._es = AsyncElasticsearch(settings.elasticsearch_url)

    @property
    def es_client(self) -> AsyncElasticsearch:
        return self._es

    async def close(self) -> None:
        await self._es.close()

    async def _get_embedding(self, text: str) -> list[float]:
        """Get text embedding from Ollama with endpoint fallback."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            base_url = settings.ollama_url.rstrip("/")

            # Native Ollama embedding endpoint.
            try:
                response = await client.post(
                    f"{base_url}/api/embed",
                    json={"model": settings.ollama_embed_model, "input": text},
                )
                if response.is_success:
                    data = response.json()
                    embeddings = data.get("embeddings") or []
                    if embeddings:
                        return embeddings[0]
            except Exception:
                pass

            # Legacy Ollama endpoint.
            try:
                response = await client.post(
                    f"{base_url}/api/embeddings",
                    json={"model": settings.ollama_embed_model, "prompt": text},
                )
                if response.is_success:
                    data = response.json()
                    vector = data.get("embedding")
                    if vector:
                        return vector
            except Exception:
                pass

            # OpenAI-compatible embedding endpoint (often used on remote gateways).
            response = await client.post(
                f"{base_url}/v1/embeddings",
                json={"model": settings.ollama_embed_model, "input": [text]},
            )
            response.raise_for_status()
            data = response.json()
            vectors = [
                item.get("embedding") for item in data.get("data", []) if item.get("embedding")
            ]
            if not vectors:
                raise ValueError("Embedding endpoint returned no vectors")
            return vectors[0]

    async def search(self, query: str) -> list[dict]:
        """Search relevant documents across all enabled sources."""
        embedding = await self._get_embedding(query)

        search_tasks = []
        if settings.rag_enable_legacy_index:
            search_tasks.append(self._search_legacy_index(embedding))
        if settings.rag_enable_mart_index:
            search_tasks.append(self._search_mart_index(embedding, query))
        if settings.cognee_enabled:
            search_tasks.append(cognee_service.search(query))

        grouped_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        documents = []
        for result in grouped_results:
            if isinstance(result, Exception):
                continue
            documents.extend(result)

        documents.sort(key=lambda item: item.get("score", 0.0), reverse=True)
        return documents[: settings.rag_top_k]

    async def _search_legacy_index(self, embedding: list[float]) -> list[dict]:
        result = await self._es.search(
            index=settings.elasticsearch_index,
            size=settings.rag_top_k,
            query={
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                        "params": {"query_vector": embedding},
                    },
                }
            },
            source_excludes=["embedding"],
        )

        documents: list[dict] = []
        for hit in result["hits"]["hits"]:
            score = hit["_score"] - 1.0
            if score < settings.rag_min_score:
                continue
            documents.append(
                {
                    "doc_id": hit.get("_id"),
                    "index_name": settings.elasticsearch_index,
                    "content": hit["_source"].get("content", ""),
                    "title": hit["_source"].get("title", ""),
                    "score": round(score, 4),
                    "source": "legacy_elastic",
                }
            )

        return documents

    async def _search_mart_index(self, embedding: list[float], query: str) -> list[dict]:
        result = await self._es.search(
            index=settings.elasticsearch_mart_index,
            size=settings.rag_top_k,
            query={
                "script_score": {
                    "query": {"match": {"text": query}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'vector') + 1.0",
                        "params": {"query_vector": embedding},
                    },
                }
            },
            source_includes=["text", "file_name"],
        )

        documents: list[dict] = []
        for hit in result["hits"]["hits"]:
            score = hit["_score"] - 1.0
            if score < settings.rag_min_score:
                continue
            source = hit.get("_source", {})
            content = source.get("text", "")
            if not content:
                continue
            documents.append(
                {
                    "doc_id": hit.get("_id"),
                    "index_name": settings.elasticsearch_mart_index,
                    "content": content,
                    "title": source.get("file_name", "mart_meet_chunk"),
                    "score": round(score, 4),
                    "source": "mart_elastic",
                }
            )

        return documents

    def build_context(self, documents: list[dict]) -> str:
        """Build context string from retrieved documents."""
        if not documents:
            return ""

        parts = []
        for i, doc in enumerate(documents, 1):
            source = doc.get("source", "unknown")
            title = doc.get("title", "Document")
            content = doc["content"]
            parts.append(f"[{i}] {title} ({source})\n{content}")

        return "\n\n---\n\n".join(parts)


rag_service = RAGService()
