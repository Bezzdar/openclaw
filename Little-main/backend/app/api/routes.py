import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from elasticsearch import NotFoundError
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import (
    ChatMessage,
    ChatRequest,
    DocumentUploadResponse,
    SessionInfo,
    SessionResetResponse,
)
from app.config import settings
from app.services.document_ingestion_service import document_ingestion_service
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.session_manager import session_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Send a message and receive a streaming SSE response.

    The stream emits events:
    - event: token   — individual text token
    - event: sources — JSON array of retrieved documents (sent once before tokens)
    - event: done    — signals end of response
    - event: error   — signals an error
    """
    session_id = request.session_id
    user_message = request.message.strip()

    if not user_message:
        raise HTTPException(status_code=400, detail="Message must not be empty")

    async def event_stream() -> AsyncGenerator[dict, None]:
        try:
            # 1. Retrieve relevant documents
            documents = await rag_service.search(user_message)
            rag_context = rag_service.build_context(documents)

            # Send sources
            yield {
                "event": "sources",
                "data": json.dumps(documents, ensure_ascii=False),
            }

            # 2. Get conversation history
            history = session_manager.get_history(session_id)

            # 3. Save user message
            session_manager.add_message(
                session_id, ChatMessage(role="user", content=user_message)
            )

            # 4. Stream LLM response
            full_response = ""
            buffered = ""
            async for token in llm_service.generate_stream(
                user_message, rag_context, history
            ):
                full_response += token
                buffered += token

                # Emit larger chunks to keep SSE readable in simple clients (curl, logs).
                if len(buffered) >= 40 or any(
                    mark in buffered for mark in [".", "!", "?", "\n", "。", "！", "？"]
                ):
                    yield {"event": "token", "data": buffered}
                    buffered = ""

            if buffered:
                yield {"event": "token", "data": buffered}

            suffix = _build_answer_suffix(documents)
            if suffix:
                full_response += suffix
                yield {"event": "token", "data": suffix}

            # 5. Save assistant response
            session_manager.add_message(
                session_id, ChatMessage(role="assistant", content=full_response)
            )

            yield {"event": "done", "data": ""}

        except Exception:
            logger.exception("Error during chat streaming")
            yield {"event": "error", "data": "Internal server error"}

    return EventSourceResponse(event_stream())


def _build_answer_suffix(documents: list[dict]) -> str:
    if not documents:
        return "\n\n[Примечание: ответ сгенерирован без опоры на загруженные учебные материалы.]"

    lines: list[str] = []
    seen_titles: set[str] = set()
    unique_docs: list[dict] = []
    for doc in documents:
        title = doc.get("title", "Источник")
        normalized_title = title.strip().lower()
        if normalized_title in seen_titles:
            continue
        seen_titles.add(normalized_title)
        unique_docs.append(doc)
        if len(unique_docs) >= 3:
            break

    for idx, doc in enumerate(unique_docs, 1):
        title = doc.get("title", "Источник")
        doc_id = doc.get("doc_id")
        index_name = doc.get("index_name")
        source = doc.get("source", "unknown")
        if doc_id and index_name:
            link = f"/api/documents/source/{index_name}/{doc_id}"
            lines.append(f"{idx}. {title} ({source}) — {link}")
        else:
            lines.append(f"{idx}. {title} ({source})")

    return "\n\n[Источники]\n" + "\n".join(lines)


@router.delete("/session/{session_id}")
async def reset_session(session_id: str):
    """Reset (clear) a chat session to start fresh context."""
    session_manager.reset_session(session_id)
    return SessionResetResponse(session_id=session_id, status="reset")


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get info about a session."""
    return SessionInfo(
        session_id=session_id,
        message_count=session_manager.get_message_count(session_id),
    )


@router.get("/session/{session_id}/history")
async def get_history(session_id: str):
    """Get full message history for a session."""
    history = session_manager.get_history(session_id)
    return {"session_id": session_id, "messages": history}


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    dataset_name: str = Form("user_uploads"),
    run_cognify: bool = Form(True),
    chunk_size: int = Form(settings.ingestion_chunk_size),
    chunk_overlap: int = Form(settings.ingestion_chunk_overlap),
):
    """
    Upload a user document and ingest it into:
    1) Elasticsearch (chunks + embeddings)
    2) Cognee (add + optional cognify) in parallel
    """
    return await document_ingestion_service.ingest_document(
        upload_file=file,
        dataset_name=dataset_name,
        run_cognify=run_cognify,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


@router.get("/documents/source/{index_name}/{doc_id}")
async def get_source_chunk(index_name: str, doc_id: str):
    allowed = {settings.elasticsearch_index, settings.elasticsearch_mart_index}
    if index_name not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported index")

    try:
        found = await rag_service.es_client.get(index=index_name, id=doc_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail="Source not found") from exc

    source = found.get("_source", {})
    payload = {
        "id": found.get("_id"),
        "index": index_name,
        "title": source.get("title") or source.get("file_name"),
        "content": source.get("content") or source.get("text"),
    }
    return payload
