from schemas.analysis import MLAnalysis, TextAnalysisResponse
from services.text_analyzer import risk_guidance


HIGH_CONFIDENCE_THRESHOLD = 0.80
MODERATE_CONFIDENCE_THRESHOLD = 0.65
HIGH_CONFIDENCE_SCORE_FLOOR = 50
MODERATE_CONFIDENCE_SCORE_FLOOR = 35


def fuse_risk(
    deterministic: TextAnalysisResponse,
    ml_analysis: MLAnalysis,
) -> TextAnalysisResponse:
    fused_score = deterministic.score

    if ml_analysis.available and ml_analysis.scam_probability is not None:
        if ml_analysis.scam_probability >= HIGH_CONFIDENCE_THRESHOLD:
            fused_score = max(fused_score, HIGH_CONFIDENCE_SCORE_FLOOR)
        elif ml_analysis.scam_probability >= MODERATE_CONFIDENCE_THRESHOLD:
            fused_score = max(fused_score, MODERATE_CONFIDENCE_SCORE_FLOOR)

    risk_level, recommended_action = risk_guidance(fused_score)
    explanation = deterministic.explanation
    if fused_score > deterministic.score:
        explanation += " The semantic classifier also found scam-like language."

    return deterministic.model_copy(
        update={
            "score": fused_score,
            "risk_level": risk_level,
            "recommended_action": recommended_action,
            "explanation": explanation,
            "ml": ml_analysis,
        }
    )
