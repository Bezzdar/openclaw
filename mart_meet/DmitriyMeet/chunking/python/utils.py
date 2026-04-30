from typing import List
from elasticsearch import Elasticsearch, helpers
from pathlib import Path
from dotenv import load_dotenv
import json
import os
import re
import urllib.request
import uuid


ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=ENV_PATH, override=True)

BATCH_SIZE = int(os.getenv("BATCH_SIZE", "16"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://10.0.10.153:11434").rstrip("/")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "qwen3-embedding:4b")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "0"))

ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://192.168.0.59:9221")
ELASTICSEARCH_USERNAME = os.getenv("ELASTICSEARCH_USERNAME")
ELASTICSEARCH_PASSWORD = os.getenv("ELASTICSEARCH_PASSWORD")


def create_elasticsearch_client() -> Elasticsearch:
    kwargs = {"verify_certs": False}
    if ELASTICSEARCH_USERNAME and ELASTICSEARCH_PASSWORD:
        kwargs["basic_auth"] = [ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD]
    return Elasticsearch(ELASTICSEARCH_URL, **kwargs)


def _post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def _embed_with_openai_endpoint(texts: list[str]) -> list[list[float]]:
    response = _post_json(
        f"{OLLAMA_BASE_URL}/v1/embeddings",
        {"model": EMBEDDING_MODEL_NAME, "input": texts},
    )
    data = response.get("data", [])
    vectors = [item.get("embedding") for item in data if item.get("embedding")]
    if not vectors:
        raise ValueError("Ollama /v1/embeddings returned empty embeddings")
    return vectors


def _embed_with_legacy_ollama_endpoint(texts: list[str]) -> list[list[float]]:
    response = _post_json(
        f"{OLLAMA_BASE_URL}/api/embed",
        {"model": EMBEDDING_MODEL_NAME, "input": texts},
    )
    vectors = response.get("embeddings", [])
    if not vectors:
        raise ValueError("Ollama /api/embed returned empty embeddings")
    return vectors


def get_embedding_with_usage(texts: list[str]) -> list[list[float]]:
    vectors: list[list[float]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start:start + BATCH_SIZE]
        try:
            batch_vectors = _embed_with_openai_endpoint(batch)
        except Exception:
            batch_vectors = _embed_with_legacy_ollama_endpoint(batch)
        vectors.extend(batch_vectors)
    return vectors


def get_embedding_dimension() -> int:
    if EMBEDDING_DIM > 0:
        return EMBEDDING_DIM
    return len(get_embedding_with_usage(["dimension_probe"])[0])


def clean_article_text(text: str) -> str:
    text = re.sub(r"10\.\d{4,9}/\S+", " ", text)
    text = re.sub(r"cвѓќ.*?\n", " ", text)
    text = re.sub(r"(\.\s*){2,}", " ", text)
    text = re.sub(r"\n\s*\d+\s*\n", "\n", text)
    text = re.sub(r"-\s*\n\s*", "", text)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text.strip()


def collect_pdf_paths(root_dir_path):
    root = Path(root_dir_path)
    pdf_list = []

    if not root.exists() or not root.is_dir():
        print("Указанный путь не существует или не является папкой.")
        print(root)
        return []

    for folder in root.iterdir():
        if folder.is_dir():
            current_folder = folder / "current" / "pdf"
            target_filename = f"{folder.name}.pdf"
            target_file_path = current_folder / target_filename

            if target_file_path.exists() and target_file_path.is_file():
                pdf_list.append(target_file_path)

    return pdf_list


def chunk_text(
        text: str,
        chunk_size: int = 1000,
        overlap: int = 200
) -> List[str]:
    if overlap >= chunk_size:
        overlap = max(0, chunk_size // 4)

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        if end >= text_length:
            break
        start = end - overlap

    return chunks


def create_index_books(es: Elasticsearch, index_name: str, dim: int = 384):
    if es.indices.exists(index=index_name):
        return

    mappings = {
        "properties": {
            "id": {
                "type": "keyword"
            },
            "file_name": {
                "type": "text"
            },
            "tags": {
                "type": "keyword"
            },
            "vector": {
                "type": "dense_vector",
                "dims": dim
            }
        }
    }

    es.indices.create(index=index_name, mappings=mappings)


def create_index_chunks(es: Elasticsearch, index_name: str, dim: int = 384):
    if es.indices.exists(index=index_name):
        return

    mappings = {
        "properties": {
            "id": {
                "type": "keyword"
            },
            "text": {
                "type": "text"
            },
            "file_name": {
                "type": "keyword"
            },
            "tags": {
                "type": "keyword"
            },
            "vector": {
                "type": "dense_vector",
                "dims": dim
            }
        }
    }

    es.indices.create(index=index_name, mappings=mappings)


def insert_chunk_records_bulk(
    elastic_search_conn,
    index_name: str,
    texts: list[str],
    file_name: str
):
    actions = []

    vectors = get_embedding_with_usage(texts)
    for vector, text in zip(vectors, texts):
        actions.append({
            "_index": index_name,
            "_id": str(uuid.uuid4()),
            "_source": {
                "id": str(uuid.uuid4()),
                "text": text,
                "file_name": file_name,
                "vector": vector,
                "tags": []
            }
        })

    helpers.bulk(elastic_search_conn, actions)


def insert_file_record(
    elastic_search_conn,
    index_name: str,
    text: str,
    file_name: str
):
    vector = get_embedding_with_usage([text])[0]

    doc = {
        "id": str(uuid.uuid4()),
        "file_name": file_name,
        "vector": vector,
        "tags": []
    }

    elastic_search_conn.index(
        index=index_name,
        document=doc
    )


def hybrid_search(
        es: Elasticsearch,
        index_name: str,
        query: str,
        k: int = 5
):
    query_vector = get_embedding_with_usage([query])[0]

    body = {
        "size": k,
        "query": {
            "bool": {
                "should": [
                    {
                        "match": {
                            "text": query
                        }
                    },
                    {
                        "script_score": {
                            "query": {"match_all": {}},
                            "script": {
                                "source": "cosineSimilarity(params.query_vector, 'vector') + 1.0",
                                "params": {
                                    "query_vector": query_vector
                                }
                            }
                        }
                    }
                ]
            }
        }
    }

    response = es.search(index=index_name, body=body)
    return response["hits"]["hits"]


def search_files_by_vector(
    elastic_search_conn,
    index_name: str,
    query_text: str,
    top_k: int = 5
):
    query_vector = get_embedding_with_usage([query_text])[0]

    query = {
        "knn": {
            "field": "vector",
            "query_vector": query_vector,
            "k": top_k,
            "num_candidates": 50
        },
        "_source": ["file_name"]
    }

    resp = elastic_search_conn.search(
        index=index_name,
        body=query
    )

    file_names = [hit["_source"]["file_name"] for hit in resp["hits"]["hits"]]
    return file_names


def hybrid_search_chunks(
    elastic_search_conn,
    index_name: str,
    query_text: str,
    file_names: list[str],
    top_k: int = 10
):
    query_vector = get_embedding_with_usage([query_text])[0]

    query = {
        "size": top_k,
        "query": {
            "script_score": {
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"text": query_text}}
                        ],
                        "filter": [
                            {"terms": {"file_name": file_names}}
                        ]
                    }
                },
                "script": {
                    "source": "cosineSimilarity(params.query_vector, 'vector') + 1.0",
                    "params": {
                        "query_vector": query_vector
                    }
                }
            }
        }
    }

    resp = elastic_search_conn.search(
        index=index_name,
        body=query
    )

    return resp["hits"]["hits"]

