"""Validated curation and deterministic paragraph/word chunking, zero overlap."""
import unicodedata
from datetime import date
import hashlib
import json
from pathlib import Path
from rag.schemas import KnowledgeChunk, KnowledgeDocument

KNOWLEDGE_PATH = Path(__file__).resolve().parent / 'knowledge' / 'guidance.json'


def load_documents(path=KNOWLEDGE_PATH):
    raw = path.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, list) or not 1 <= len(data) <= 200:
        raise ValueError('Expected a bounded list of curated documents')
    documents = [KnowledgeDocument.model_validate(row) for row in data]
    if len({d.id for d in documents}) != len(documents):
        raise ValueError('Duplicate knowledge id')
    if any(d.reviewed_on > date.today() for d in documents):
        raise ValueError("Source review date cannot be in the future")
    if len({" ".join(unicodedata.normalize("NFKC", d.content).casefold().split()) for d in documents}) != len(documents):
        raise ValueError('Duplicate knowledge content')
    return sorted(documents, key=lambda d: d.id), hashlib.sha256(raw).hexdigest()


def chunk_documents(documents):
    chunks = []
    for doc in documents:
        pieces = []
        for paragraph in doc.content.split('\n\n'):
            current = ''
            for word in paragraph.split():
                if len(word) > 800:
                    raise ValueError('Unchunkable knowledge token')
                if current and len(current) + len(word) + 1 > 800:
                    pieces.append(current)
                    current = ''
                current = f'{current} {word}'.strip()
            if current:
                pieces.append(current)
        for i, text in enumerate(pieces):
            chunks.append(KnowledgeChunk(chunk_id=f'{doc.id}-{i+1}', source_id=doc.id,
                text=text, topics=doc.topics, signal_codes=doc.signal_codes))
    return chunks
