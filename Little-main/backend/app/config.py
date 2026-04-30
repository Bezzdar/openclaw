from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Elasticsearch
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index: str = "knowledge_base"
    elasticsearch_mart_index: str = "chunking_index"
    rag_enable_legacy_index: bool = True
    rag_enable_mart_index: bool = True

    # Ollama
    ollama_url: str = "http://10.0.10.153:11434"
    ollama_model: str = "qwen3.5:4b"
    ollama_embed_model: str = "qwen3-embedding:0.6b"

    # RAG
    rag_top_k: int = 5
    rag_min_score: float = 0.3

    # Cognee integration
    cognee_enabled: bool = False
    cognee_url: str = "http://localhost:8001"
    cognee_search_type: str = "CHUNKS"
    cognee_default_dataset: str | None = None
    cognee_api_token: str | None = None
    cognee_timeout_sec: float = 30.0

    # Ingestion
    ingestion_chunk_size: int = 1200
    ingestion_chunk_overlap: int = 200
    ingestion_embedding_batch_size: int = 8
    ingestion_embedding_timeout_sec: float = 300.0

    # Sessions
    session_max_history: int = 20
    session_ttl_minutes: int = 60
    session_max_count: int = 1000

    model_config = {"env_prefix": "RAG_", "env_file": ".env"}


settings = Settings()
