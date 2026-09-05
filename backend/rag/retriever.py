"""Read-only, local retrieval. Neither this module nor the KB can set risk."""
from datetime import date
import hashlib
import json
import os
import re
from threading import RLock
import numpy as np
from ml.embeddings import MODEL_NAME, get_embedding_model
from rag.build_index import INDEX_DIR, SCHEMA_VERSION, model_fingerprint, normalized_matrix
from rag.knowledge import load_documents, chunk_documents
from rag.schemas import Grounding, GroundingResult

# Retrieval-only relevance gates, independent of V3/V4/V5 scoring constants.
TOPIC_MIN_SIMILARITY = .25
SEMANTIC_MIN_SIMILARITY = .72
SEMANTIC_MIN_MARGIN = .08
STAGE_TOPICS = {
    'VERIFICATION_PRETEXT': {'banking_kyc'}, 'LINK_REDIRECTION': {'phishing'},
    'CREDENTIAL_HARVESTING': {'credentials'}, 'PAYMENT_EXTRACTION': {'payment_upi'},
    'REMOTE_ACCESS': {'remote_access'}, 'AUTHENTICATION_TAKEOVER': {'otp'},
    'INVESTMENT_LURE': {'investment'},
}
# Topic cues are for reference relevance only, including educational/safety language.
# Generic urgency, "bank", "code", "money", or "recovery" alone are not topic cues.
TOPIC_PATTERNS = {
    'otp': r'\botp\b|one[ -]time password|ओटीपी|ஓடிபி',
    'credentials': r'\bpasswords?\b|\bpassphrase\b|पासवर्ड|கடவுச்சொல்',
    'remote_access': r'\banydesk\b|\bteamviewer\b|remote[ -](?:access|control)|screen[ -]shar',
    'banking_kyc': r'\bkyc\b|know your customer',
    'phishing': r'\bphishing\b|(?:click|open|follow) (?:this |the |a )?(?:link|url)',
    'payment_upi': r'\bupi\b|\bqr code\b',
    'account_threat': r'account.{0,25}(?:block|clos|deactivat|suspend)|(?:block|clos|deactivat|suspend).{0,25}account',
    'government_impersonation': r'digital arrest|(?:police|court|government).{0,35}(?:pay|transfer|arrest|fine)',
    'investment': r'\binvestment\b|\binvest\b|guaranteed (?:profit|return)|trading (?:app|platform)',
    'recovery': r'(?:recover|recovery).{0,45}(?:scam|lost|stolen|funds|money)|(?:scam|lost|stolen).{0,45}(?:recover|recovery)',
}
# Explicit multilingual topic names supply lexical relevance when an English
# reference has poor cross-language cosine similarity. These are curation cues,
# not translated knowledge, detector signals, or general words such as "bank".
MULTILINGUAL_TOPIC_ALIASES = {
    'otp': ('ओटीपी', 'ஓடிபி', 'ஒருமுறை கடவுச்சொல்'),
    'credentials': ('पासवर्ड', 'கடவுச்சொல்'),
    'remote_access': ('रिमोट एक्सेस', 'स्क्रीन शेयर', 'தொலைநிலை அணுகல்'),
    'phishing': ('फिशिंग', 'फ़िशिंग', 'பிஷிங்'),
    'payment_upi': ('यूपीआई', 'क्यूआर', 'யூபிஐ', 'கியூஆர்'),
}


def lexical_topics(text):
    import unicodedata
    value = unicodedata.normalize('NFKC', text).casefold()
    return {topic for topic, aliases in MULTILINGUAL_TOPIC_ALIASES.items()
            if any(alias in value for alias in aliases)}

_lock = RLock()
_cached_key = None
_cached_index = None


def enabled():
    return os.getenv('RAG_ENABLED', 'true').strip().lower() == 'true'


def clear_index_cache():
    global _cached_key, _cached_index
    with _lock:
        _cached_key = _cached_index = None


def load_index():
    """Cache only curated rows/vectors. Check file identities before reusing them."""
    global _cached_key, _cached_index
    from rag.knowledge import KNOWLEDGE_PATH
    paths = (INDEX_DIR / 'metadata.json', INDEX_DIR / 'vectors.npy', KNOWLEDGE_PATH)
    key = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in paths)
    with _lock:
        if _cached_key == key and _cached_index is not None:
            return _cached_index
        docs, knowledge_hash = load_documents()
        chunks = chunk_documents(docs)
        meta = json.loads(paths[0].read_text())
        if (meta['schema_version'] != SCHEMA_VERSION or meta['embedding_model'] != MODEL_NAME
                or meta['embedding_dimension'] != 384 or meta['knowledge_sha256'] != knowledge_hash
                or meta['document_count'] != len(docs) or meta['chunk_count'] != len(chunks)
                or meta['chunks'] != [c.model_dump(mode='json') for c in chunks]
                or meta['embedding_version'] != model_fingerprint()
                or meta['vectors_sha256'] != hashlib.sha256(paths[1].read_bytes()).hexdigest()):
            raise ValueError('Knowledge index requires a rebuild')
        matrix = normalized_matrix(np.load(paths[1], allow_pickle=False), len(chunks))
        matrix.setflags(write=False)
        _cached_index = ({d.id: d for d in docs}, chunks, matrix)
        _cached_key = key
        return _cached_index


def retrieve_guidance(text: str, signal_codes=(), stages=()) -> Grounding:
    if not enabled():
        return Grounding()
    try:
        docs, chunks, matrix = load_index()
        signals = set(signal_codes)
        stage_set = set(stages)
        topics = {topic for topic, pattern in TOPIC_PATTERNS.items() if re.search(pattern, text, re.I)}
        explicit_topics = lexical_topics(text)
        topics |= explicit_topics
        similarities = None
        if text.strip():
            query = np.asarray(get_embedding_model().encode([text], normalize_embeddings=True)[0], dtype=np.float32)
            norm = np.linalg.norm(query)
            if query.shape != (384,) or not np.isfinite(query).all() or norm <= 0:
                return Grounding()
            similarities = np.clip(matrix @ (query / norm), -1, 1)
        ranked = []
        sorted_sims = sorted(similarities, reverse=True) if similarities is not None else []
        semantic_clear = len(sorted_sims) == 1 or (len(sorted_sims) > 1 and sorted_sims[0] - sorted_sims[1] >= SEMANTIC_MIN_MARGIN)
        for pos, chunk in enumerate(chunks):
            matched = sorted(signals.intersection(chunk.signal_codes))
            matched_topics = sorted(topics.intersection(chunk.topics))
            matched_stages = sorted(stage for stage in stage_set if STAGE_TOPICS.get(stage, set()).intersection(chunk.topics))
            similarity = float(similarities[pos]) if similarities is not None else None
            # Canonical signal/stage match is sufficient topic relevance. Pure text
            # topic matching requires cosine support; pure semantic needs a margin.
            if matched:
                relevance = 'signal'
            elif matched_stages:
                relevance = 'stage'
            elif matched_topics and (explicit_topics.intersection(chunk.topics) or
                    similarity is not None and similarity >= TOPIC_MIN_SIMILARITY):
                relevance = 'topic'
            elif (not signals and not topics and not stage_set and similarity is not None
                    and similarity >= SEMANTIC_MIN_SIMILARITY and semantic_clear
                    and similarity == float(sorted_sims[0])):
                relevance = 'semantic'
            else:
                continue
            score = (.55 * bool(matched) + .10 * bool(matched_stages) + .15 * bool(matched_topics)
                     + .20 * max(similarity or 0, 0))
            ranked.append((score, chunk.chunk_id, chunk, matched, matched_topics, matched_stages, similarity, relevance))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        results = []
        seen_publications = set()
        for _, _, chunk, matched, matched_topics, matched_stages, similarity, relevance in ranked:
            doc = docs[chunk.source_id]
            publication = doc.source_url.split('#')[0]
            if publication in seen_publications:
                continue
            seen_publications.add(publication)
            results.append(GroundingResult(source_id=doc.id, chunk_id=chunk.chunk_id,
                title=doc.title, source_name=doc.source_name, source_url=doc.source_url,
                guidance=chunk.text, topics=chunk.topics, matched_signals=matched,
                matched_topics=matched_topics, matched_stages=matched_stages,
                similarity=similarity, relevance=relevance, reviewed_on=doc.reviewed_on,
                review_due=(date.today() - doc.reviewed_on).days > 180))
            if len(results) == 3:
                break
        # Available means index/model worked, even if relevance caused abstention.
        return Grounding(available=True, results=results)
    except Exception:
        # Optional explanation fails closed without exposing local paths or internals.
        return Grounding()
