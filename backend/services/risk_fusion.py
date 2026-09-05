from schemas.analysis import MLAnalysis, TextAnalysisResponse
from schemas.semantic import SemanticAnalysis
from schemas.signals import SignalCode
from services.text_analyzer import SIGNAL_LABELS, risk_guidance


ML_HIGH_THRESHOLD = 0.80
ML_MODERATE_THRESHOLD = 0.65
SEMANTIC_HIGH_THRESHOLD = 0.85
SEMANTIC_MODERATE_THRESHOLD = 0.70
SEMANTIC_ELEVATED_THRESHOLD = 0.55
SEMANTIC_SIGNAL_CONFIDENCE = 0.70


def fuse_risk(
    deterministic: TextAnalysisResponse,
    ml_analysis: MLAnalysis,
    semantic_analysis: SemanticAnalysis | None = None,
) -> TextAnalysisResponse:
    semantic = semantic_analysis or SemanticAnalysis(available=False)
    fused_score = _apply_ml_floor(deterministic.score, ml_analysis)
    fused_score = _apply_semantic_floor(fused_score, semantic)
    merged_codes = _merge_semantic_signals(deterministic, semantic)
    merged_labels = [
        label for code, label in SIGNAL_LABELS.items() if code in merged_codes
    ]

    risk_level, recommended_action = risk_guidance(fused_score)
    explanation = deterministic.explanation
    if semantic.available and not semantic.is_safety_warning and semantic.explanation:
        explanation = semantic.explanation
    elif fused_score > deterministic.score:
        explanation += " The semantic classifier also found scam-like language."

    return deterministic.model_copy(
        update={
            "score": fused_score,
            "risk_level": risk_level,
            "recommended_action": recommended_action,
            "explanation": explanation,
            "signals": merged_labels,
            "signal_codes": merged_codes,
            "ml": ml_analysis,
            "semantic": semantic,
        }
    )


def _apply_ml_floor(score: int, ml_analysis: MLAnalysis) -> int:
    if not ml_analysis.available or ml_analysis.scam_probability is None:
        return score
    if ml_analysis.scam_probability >= ML_HIGH_THRESHOLD:
        return max(score, 50)
    if ml_analysis.scam_probability >= ML_MODERATE_THRESHOLD:
        return max(score, 35)
    return score


def _apply_semantic_floor(score: int, semantic: SemanticAnalysis) -> int:
    if (
        not semantic.available
        or semantic.is_safety_warning
        or semantic.risk_score is None
    ):
        return score
    if semantic.risk_score >= SEMANTIC_HIGH_THRESHOLD:
        return max(score, 70)
    if semantic.risk_score >= SEMANTIC_MODERATE_THRESHOLD:
        return max(score, 50)
    if semantic.risk_score >= SEMANTIC_ELEVATED_THRESHOLD:
        return max(score, 35)
    return score


def _merge_semantic_signals(
    deterministic: TextAnalysisResponse,
    semantic: SemanticAnalysis,
) -> set[SignalCode]:
    merged = set(deterministic.signal_codes)
    if not semantic.available or semantic.is_safety_warning:
        return merged
    merged.update(
        signal.code
        for signal in semantic.signals
        if signal.confidence >= SEMANTIC_SIGNAL_CONFIDENCE
    )
    return merged
