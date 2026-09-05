"""One shared, strictly local MiniLM instance for V4 and knowledge retrieval."""
from functools import lru_cache
from pathlib import Path
from threading import RLock

EMBEDDING_MODEL_PATH = Path(__file__).resolve().parent / 'artifacts' / 'embedding_model'
MODEL_NAME = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
_lock = RLock()


@lru_cache(maxsize=1)
def _load_embedding_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(str(EMBEDDING_MODEL_PATH), local_files_only=True)


def get_embedding_model():
    with _lock:
        return _load_embedding_model()
