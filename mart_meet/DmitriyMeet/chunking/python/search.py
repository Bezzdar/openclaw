import os
import sys
from pathlib import Path
from dotenv import dotenv_values

from utils import (
    create_elasticsearch_client,
    hybrid_search_chunks,
    search_files_by_vector,
)

ENV_PATH = Path(__file__).with_name(".env")
config = dotenv_values(ENV_PATH)
TOP_K = int(config.get("TOP_K") or os.getenv("TOP_K", "5"))
ES = create_elasticsearch_client()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def library_search(query_text: str):
    topics_names = search_files_by_vector(ES, "book_index", query_text, top_k=TOP_K)
    result = hybrid_search_chunks(ES, "chunking_index", query_text, topics_names, top_k=TOP_K)
    return result


if __name__ == "__main__":
    print(library_search("what do you can tell me about Graphite?"))
