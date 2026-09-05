"""Bounded, synthetic-only training references. Query embeddings are never cached."""
import hashlib
import json
import os
from pathlib import Path
from threading import RLock
import numpy as np
from schemas.intelligence import SemanticNeighbors, SemanticNeighbor

DATA = Path(__file__).resolve().parent / 'data'
_lock = RLock()
_cached_model = None
_cached_index = None


def enabled():
    return os.getenv('ML_EXPLANATIONS_ENABLED', 'true').strip().lower() == 'true'


def clear_reference_cache():
    global _cached_model, _cached_index
    with _lock:
        _cached_model = _cached_index = None


def reference_index(model):
    global _cached_model, _cached_index
    with _lock:
        if _cached_model is model and _cached_index is not None:
            return _cached_index
        from ml.classifier import V2_DIR
        raw=(DATA/'train_v2.json').read_bytes()
        expected=json.loads((DATA/'v2_manifest.json').read_text())['train_v2.json']
        trained=json.loads((V2_DIR/'metadata.json').read_text())['dataset_hashes']['train_v2.json']
        if hashlib.sha256(raw).hexdigest()!=expected or expected!=trained:
            raise ValueError('Reference provenance mismatch')
        rows=json.loads(raw)
        if not rows or len(rows)>500 or any(r.get('source_type')!='synthetic_manual' or r.get('label') not in ('scam','safe') or len(r.get('text',''))>1000 for r in rows):
            raise ValueError('References are not approved synthetic examples')
        matrix=np.asarray(model.encode([r['text'] for r in rows],normalize_embeddings=True),dtype=float)
        if matrix.ndim!=2 or len(matrix)!=len(rows) or not np.isfinite(matrix).all():
            raise ValueError('Invalid reference matrix')
        norms=np.linalg.norm(matrix,axis=1,keepdims=True)
        if (norms==0).any(): raise ValueError('Empty reference embedding')
        matrix=matrix/norms
        _cached_index=(rows,matrix)
        _cached_model=model
        return _cached_index


def explain_neighbors(model, query_embedding, version):
    if not enabled() or version!='v2':
        return SemanticNeighbors()
    try:
        rows,matrix=reference_index(model)
        query=np.asarray(query_embedding,dtype=float).reshape(-1)
        norm=np.linalg.norm(query)
        if not np.isfinite(query).all() or norm==0: return SemanticNeighbors()
        similarities=np.clip(matrix @ (query/norm),-1,1)
        def nearest(label):
            indices=[i for i in np.argsort(-similarities,kind='stable') if rows[i]['label']==label][:2]
            return [SemanticNeighbor(text=rows[i]['text'],similarity=float(similarities[i]),language=rows[i]['language'],category=rows[i]['category']) for i in indices]
        return SemanticNeighbors(available=True,suspicious=nearest('scam'),safe=nearest('safe'))
    except Exception:
        # Missing or unsafe explanation data must never disable successful ML inference.
        return SemanticNeighbors()
