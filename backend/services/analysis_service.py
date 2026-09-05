from ml.classifier import predict_scam_probability
from schemas.analysis import TextAnalysisResponse
from services.risk_fusion import fuse_risk
from services.text_analyzer import analyze_text as analyze_text_deterministically


def analyze_text(text: str) -> TextAnalysisResponse:
    deterministic = analyze_text_deterministically(text)
    ml_analysis = predict_scam_probability(text)
    return fuse_risk(deterministic, ml_analysis)
