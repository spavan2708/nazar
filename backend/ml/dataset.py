"""Versioned research data. Frozen test content is never loaded by training."""
import hashlib
import json
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from ml.v2_data import normalized
from schemas.signals import SignalCode

ROOT = Path(__file__).resolve().parent / 'data'
DATA = ROOT / 'hardening'

class Example(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=10000)
    label: Literal['scam', 'safe']
    language: str
    language_style: str
    category: str
    difficulty: str
    source_type: Literal['synthetic_manual', 'synthetic_authored', 'synthetic_augmented']
    native_reviewed: bool = False
    group: str
    parent_id: str | None = None
    noise_type: str | None = None
    signals: list[SignalCode] | None = None  # None = unannotated, NOT no signals
    safety_context: bool | None = None
    notes: str


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_split(split):
    if split not in ('train', 'validation', 'test'):
        raise ValueError('Unknown split')
    manifest = json.loads((DATA / 'manifest.json').read_text())
    entry = manifest['splits'][split]
    path = ROOT / entry['path']
    if sha(path) != entry['sha256']:
        raise ValueError('Frozen dataset fingerprint mismatch')
    rows = json.loads(path.read_text())
    if split != 'test':
        rows = [Example.model_validate(row).model_dump(mode='json') for row in rows]
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate IDs')
    return rows


def quality(splits, embeddings=None):
    """Exact/lexical overlap blocks splits; semantic candidates require human review."""
    records = [(split, row) for split, rows in splits.items() for row in rows]
    conflicts, semantic = [], []
    duplicates = []
    seen_text = {}
    for split, row in records:
        key = normalized(row["text"])
        if key in seen_text:
            duplicates.append(dict(left=seen_text[key], right=row["id"]))
        seen_text[key] = row["id"]
    for i, (split, row) in enumerate(records):
        for j in range(i):
            other_split, other = records[j]
            if split == other_split:
                continue
            exact = normalized(row['text']) == normalized(other['text'])
            near = SequenceMatcher(None, normalized(row['text']), normalized(other['text']), autojunk=False).ratio() >= .90
            group = row['group'] == other['group']
            if exact or near or group:
                conflicts.append(dict(left=other['id'], right=row['id'], exact=exact, lexical=near, group=group))
            if embeddings is not None:
                sim = float(embeddings[i] @ embeddings[j])
                if sim >= .95:
                    semantic.append(dict(left=other['id'], right=row['id'], similarity=sim))
    return dict(counts={k:len(v) for k,v in splits.items()},
        breakdown={k:{field:dict(Counter(str(r.get(field)) for r in rows)) for field in ('label','language','category','source_type')} for k,rows in splits.items()},
        normalized_duplicate_records=duplicates,
        blocking_cross_split_overlaps=conflicts, semantic_review_candidates=semantic,
        semantic_checked=embeddings is not None,
        caveat='Synthetic scenarios are not independent real-world observations. Cosine proximity is a review flag, not proof of label equivalence.')


def assert_training_separation(train, validation):
    result = quality({'train':train, 'validation':validation})
    if result['blocking_cross_split_overlaps']:
        raise ValueError('Training/validation leakage detected')
