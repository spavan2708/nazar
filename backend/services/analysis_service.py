from rag.retriever import retrieve_guidance
from time import perf_counter
from services.orchestration import describe
from services.limits import MAX_TEXT_CHARS
from services.investigation_stages import derive_stages
from ml.classifier import predict_scam_probability
from schemas.analysis import TextAnalysisResponse
from schemas.url import URLAnalysis
from services.language_detection import identify_language
from services.llm.semantic_analyzer import analyze_semantics
from services.risk_fusion import fuse_risk
from services.text_analyzer import SIGNAL_SEVERITY, analyze_text as analyze_text_deterministically
from schemas.signals import SignalCode
from services.url_intelligence import extract_url_analysis


def analyze_text(text: str, *, precomputed_urls: tuple[list[URLAnalysis], bool] | None = None) -> TextAnalysisResponse:
    if not text.strip() or len(text) > MAX_TEXT_CHARS:
        raise ValueError("Text must contain 1–10000 characters")
    timings = {}
    started = perf_counter()
    language = identify_language(text)
    timings["language"] = (perf_counter() - started) * 1000
    started = perf_counter()
    urls, urls_truncated = precomputed_urls if precomputed_urls is not None else extract_url_analysis(text)
    timings["url"] = (perf_counter() - started) * 1000
    started = perf_counter()
    # Use the existing canonical LINK_REQUEST weight, not the structural score
    # as a new message score/floor. Multiple related IDN flags count as one group.
    link_evidence = any(
        result.valid and result.evidence_groups >= 2
        and (result.structural_risk_score or 0) >= SIGNAL_SEVERITY[SignalCode.LINK_REQUEST]
        for result in urls
    )
    deterministic = (analyze_text_deterministically(text, url_evidence=True)
        if link_evidence else analyze_text_deterministically(text))
    timings["rules"] = (perf_counter() - started) * 1000
    started = perf_counter()
    ml_analysis = predict_scam_probability(text)
    timings["ml_including_embedding_and_neighbors"] = (perf_counter() - started) * 1000
    started = perf_counter()
    semantic_analysis = analyze_semantics(text)
    timings["semantic"] = (perf_counter() - started) * 1000
    result = fuse_risk(deterministic, ml_analysis, semantic_analysis)
    started = perf_counter()
    grounding = retrieve_guidance(text, result.signal_codes, derive_stages(result))
    timings["rag"] = (perf_counter() - started) * 1000
    result = result.model_copy(
        update={"grounding": grounding, "original_text": text, "urls": urls, "urls_truncated": urls_truncated, **language.model_dump()}
    )

    result.orchestration = describe(result)
    result.timings_ms = {key: round(value, 3) for key, value in timings.items()}
    return result
