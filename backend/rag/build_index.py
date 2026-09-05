"""Run from backend: python -m rag.build_index. Never downloads or trains."""
import hashlib
import json
from importlib.metadata import version
from pathlib import Path
import numpy as np
from ml.embeddings import EMBEDDING_MODEL_PATH, MODEL_NAME, get_embedding_model
from rag.knowledge import load_documents, chunk_documents

INDEX_DIR = Path(__file__).resolve().parent / 'index'
SCHEMA_VERSION = 1


def model_fingerprint():
    digest = hashlib.sha256()
    files = sorted(p for p in EMBEDDING_MODEL_PATH.rglob('*') if p.is_file() and p.name != 'README.md')
    if not files or not any(p.suffix == '.safetensors' for p in files):
        raise ValueError('Local embedding model is missing')
    for path in files:
        digest.update(str(path.relative_to(EMBEDDING_MODEL_PATH)).encode())
        with path.open('rb') as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(block)
    return digest.hexdigest()


def normalized_matrix(values, count):
    matrix = np.asarray(values, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[0] != count or matrix.shape[1] != 384 or not np.isfinite(matrix).all():
        raise ValueError('Invalid MiniLM index dimensions or values')
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if (norms <= 0).any():
        raise ValueError('Zero reference embedding')
    return matrix / norms


def build_index(output_dir=INDEX_DIR):
    docs, knowledge_hash = load_documents()
    chunks = chunk_documents(docs)
    # Exactly the chunk text is encoded; no query or user evidence is accepted.
    matrix = normalized_matrix(get_embedding_model().encode(
        [c.text for c in chunks], normalize_embeddings=True), len(chunks))
    output_dir.mkdir(parents=True, exist_ok=True)
    # Metadata is replaced last, so partial/mixed generations fail integrity checks.
    vector_tmp = output_dir / 'vectors.tmp'
    with vector_tmp.open('wb') as handle:
        np.save(handle, matrix, allow_pickle=False)
    vector_hash = hashlib.sha256(vector_tmp.read_bytes()).hexdigest()
    metadata = {
        'schema_version': SCHEMA_VERSION, 'embedding_model': MODEL_NAME,
        'embedding_version': model_fingerprint(), 'embedding_dimension': 384,
        'sentence_transformers_version': version('sentence-transformers'),
        'numpy_version': version('numpy'), 'knowledge_sha256': knowledge_hash,
        'vectors_sha256': vector_hash, 'document_count': len(docs), 'chunk_count': len(chunks),
        'chunking': 'paragraphs, max 800 characters, word boundaries, zero overlap',
        'chunks': [c.model_dump(mode='json') for c in chunks],
    }
    meta_tmp = output_dir / 'metadata.tmp'
    meta_tmp.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True)+'\n')
    vector_tmp.replace(output_dir / 'vectors.npy')
    meta_tmp.replace(output_dir / 'metadata.json')
    return metadata


if __name__ == '__main__':
    info = build_index()
    print(f"Built {info['document_count']} documents / {info['chunk_count']} chunks with {info['embedding_model']}")
