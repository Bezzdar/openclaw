from __future__ import annotations

import asyncio
import io
import re
import uuid
from pathlib import Path

import httpx
from docx import Document
from elasticsearch.helpers import async_bulk
from fastapi import HTTPException, UploadFile
from pypdf import PdfReader

from app.config import settings
from app.services.cognee_service import cognee_service
from app.services.rag_service import rag_service


SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}


class DocumentIngestionService:
    async def ingest_document(
        self,
        *,
        upload_file: UploadFile,
        dataset_name: str,
        run_cognify: bool,
        chunk_size: int,
        chunk_overlap: int,
    ) -> dict:
        file_name = upload_file.filename or "uploaded_document"
        extension = Path(file_name).suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported extension '{extension}'. Allowed: txt, pdf, docx",
            )

        file_bytes = await upload_file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        text = self._extract_text(file_bytes, extension).strip()
        if not text:
            raise HTTPException(status_code=400, detail="No text extracted from the uploaded file")

        chunks = self._split_text(text, chunk_size=chunk_size, overlap=chunk_overlap)
        if not chunks:
            raise HTTPException(status_code=400, detail="Document chunking produced no chunks")

        elastic_task = asyncio.create_task(self._index_chunks(file_name=file_name, chunks=chunks))
        cognee_task = asyncio.create_task(
            cognee_service.add_and_cognify(
                file_name=file_name,
                file_bytes=file_bytes,
                dataset_name=dataset_name,
                run_cognify=run_cognify,
            )
        )

        elastic_result, cognee_result = await asyncio.gather(elastic_task, cognee_task)

        return {
            "file_name": file_name,
            "chunks_created": len(chunks),
            "elastic_index": settings.elasticsearch_index,
            "elastic_indexed": elastic_result["indexed"],
            "cognee": cognee_result,
        }

    def _extract_text(self, file_bytes: bytes, extension: str) -> str:
        if extension == ".txt":
            for encoding in ("utf-8", "cp1251", "latin-1"):
                try:
                    return file_bytes.decode(encoding)
                except UnicodeDecodeError:
                    continue
            return file_bytes.decode("utf-8", errors="ignore")

        if extension == ".pdf":
            reader = PdfReader(io.BytesIO(file_bytes))
            parts = []
            for page in reader.pages:
                parts.append(page.extract_text() or "")
            return "\n".join(parts)

        if extension == ".docx":
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join(paragraph.text for paragraph in doc.paragraphs)

        return ""

    def _split_text(self, text: str, chunk_size: int, overlap: int) -> list[str]:
        # Normalize whitespace within lines but preserve paragraph breaks
        lines = text.splitlines()
        normalized = "\n".join(" ".join(line.split()) for line in lines)
        # Collapse 3+ newlines into double newlines
        normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
        if not normalized:
            return []

        if overlap >= chunk_size:
            overlap = max(0, chunk_size // 4)

        chunks: list[str] = []
        start = 0
        while start < len(normalized):
            end = min(start + chunk_size, len(normalized))
            chunks.append(normalized[start:end])
            if end == len(normalized):
                break
            start = end - overlap
        return chunks

    async def _index_chunks(self, *, file_name: str, chunks: list[str]) -> dict:
        embeddings = await self._embed_chunks(chunks)
        if len(embeddings) != len(chunks):
            raise HTTPException(
                status_code=500,
                detail="Embedding service returned unexpected number of vectors",
            )

        await self._ensure_legacy_index(len(embeddings[0]))

        actions = []
        for chunk, embedding in zip(chunks, embeddings):
            actions.append(
                {
                    "_index": settings.elasticsearch_index,
                    "_id": str(uuid.uuid4()),
                    "_source": {
                        "title": file_name,
                        "content": chunk,
                        "embedding": embedding,
                    },
                }
            )

        indexed, _errors = await async_bulk(
            rag_service.es_client,
            actions,
            refresh="wait_for",
            raise_on_error=False,
        )

        return {"indexed": indexed}

    async def _embed_chunks(self, chunks: list[str]) -> list[list[float]]:
        timeout = httpx.Timeout(settings.ingestion_embedding_timeout_sec)
        batch_size = max(1, settings.ingestion_embedding_batch_size)
        base_url = settings.ollama_url.rstrip("/")
        vectors: list[list[float]] = []

        async with httpx.AsyncClient(timeout=timeout) as client:
            for start in range(0, len(chunks), batch_size):
                batch = chunks[start : start + batch_size]
                batch_vectors = await self._embed_batch(client, base_url, batch)
                vectors.extend(batch_vectors)

        if not vectors or len(vectors) != len(chunks):
            raise HTTPException(status_code=500, detail="No embeddings returned by Ollama")
        return vectors

    async def _embed_batch(
        self, client: httpx.AsyncClient, base_url: str, batch: list[str]
    ) -> list[list[float]]:
        # Native Ollama endpoint.
        try:
            response = await client.post(
                f"{base_url}/api/embed",
                json={"model": settings.ollama_embed_model, "input": batch},
            )
            if response.is_success:
                payload = response.json()
                embeddings = payload.get("embeddings") or []
                if embeddings and len(embeddings) == len(batch):
                    return embeddings
        except Exception:
            pass

        # Legacy Ollama endpoint (single prompt per call).
        legacy_vectors: list[list[float]] = []
        legacy_ok = True
        for chunk in batch:
            try:
                legacy_response = await client.post(
                    f"{base_url}/api/embeddings",
                    json={"model": settings.ollama_embed_model, "prompt": chunk},
                )
            except Exception:
                legacy_ok = False
                break
            if not legacy_response.is_success:
                legacy_ok = False
                break
            vector = legacy_response.json().get("embedding")
            if not vector:
                legacy_ok = False
                break
            legacy_vectors.append(vector)
        if legacy_ok and len(legacy_vectors) == len(batch):
            return legacy_vectors

        # OpenAI-compatible endpoint.
        response = await client.post(
            f"{base_url}/v1/embeddings",
            json={"model": settings.ollama_embed_model, "input": batch},
        )
        response.raise_for_status()
        payload = response.json()
        vectors = [item.get("embedding") for item in payload.get("data", []) if item.get("embedding")]
        if len(vectors) != len(batch):
            raise HTTPException(status_code=500, detail="Embedding batch response is incomplete")
        return vectors

    async def _ensure_legacy_index(self, embedding_dims: int) -> None:
        exists = await rag_service.es_client.indices.exists(index=settings.elasticsearch_index)
        if exists:
            return

        await rag_service.es_client.indices.create(
            index=settings.elasticsearch_index,
            mappings={
                "properties": {
                    "title": {"type": "text"},
                    "content": {"type": "text"},
                    "embedding": {"type": "dense_vector", "dims": embedding_dims},
                }
            },
        )


document_ingestion_service = DocumentIngestionService()
