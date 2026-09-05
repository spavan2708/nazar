from rag.schemas import Grounding
from services.orchestration import Orchestration
from pydantic import BaseModel, Field, field_validator

from schemas.language import LanguageMetadata
from schemas.intelligence import Intelligence, SemanticNeighbors
from schemas.semantic import SemanticAnalysis
from schemas.signals import SignalCode
from schemas.url import URLAnalysis


from services.limits import MAX_TEXT_CHARS


class TextAnalysisRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text must not be blank")
        return value.strip()


class AnalysisContext(BaseModel):
    is_safety_warning: bool = False
    is_action_request: bool = False
    has_contextual_pressure: bool = False


class MLAnalysis(BaseModel):
    semantic_neighbors: SemanticNeighbors = Field(default_factory=SemanticNeighbors, exclude=True)
    available: bool
    scam_probability: float | None = None
    model_version: str | None = None
    input_truncated: bool = False


class TextAnalysisResponse(LanguageMetadata):
    orchestration: Orchestration | None = None
    timings_ms: dict[str, float] = Field(default_factory=dict)
    grounding: Grounding | None = None
    intelligence: Intelligence | None = None
    original_text: str | None = None
    urls: list[URLAnalysis] = Field(default_factory=list)
    urls_truncated: bool = False
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
