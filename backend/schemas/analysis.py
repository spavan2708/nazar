from pydantic import BaseModel, Field, field_validator

from schemas.semantic import SemanticAnalysis
from schemas.signals import SignalCode


class TextAnalysisRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text must not be blank")
        return value.strip()


class AnalysisContext(BaseModel):
    is_safety_warning: bool = False
    is_action_request: bool = False


class MLAnalysis(BaseModel):
    available: bool
    scam_probability: float | None = None
    model_version: str | None = None


class TextAnalysisResponse(BaseModel):
    score: int
    risk_level: str
    signals: list[str]
    explanation: str
    recommended_action: str
    ml: MLAnalysis | None = None
    semantic: SemanticAnalysis | None = None
    signal_codes: set[SignalCode] = Field(default_factory=set, exclude=True)
    context: AnalysisContext = Field(default_factory=AnalysisContext, exclude=True)
    patterns: list[str] = Field(default_factory=list, exclude=True)
