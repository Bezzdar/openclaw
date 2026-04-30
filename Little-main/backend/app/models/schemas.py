from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class SessionInfo(BaseModel):
    session_id: str
    message_count: int


class SessionResetResponse(BaseModel):
    session_id: str
    status: str


class CogneeIngestionStatus(BaseModel):
    enabled: bool
    dataset_name: str
    add_status: str
    cognify_status: str
    detail: str | None = None


class DocumentUploadResponse(BaseModel):
    file_name: str
    chunks_created: int
    elastic_index: str
    elastic_indexed: int
    cognee: CogneeIngestionStatus
