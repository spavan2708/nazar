from enum import StrEnum
from pydantic import BaseModel, Field
from schemas.signals import SignalCode


class AgreementStatus(StrEnum):
    STRONG_AGREEMENT = 'STRONG_AGREEMENT'
    PARTIAL_AGREEMENT = 'PARTIAL_AGREEMENT'
    ML_ONLY = 'ML_ONLY'
    RULES_ONLY = 'RULES_ONLY'
    LLM_ONLY = 'LLM_ONLY'
    CONFLICTING = 'CONFLICTING'
    INSUFFICIENT_EVIDENCE = 'INSUFFICIENT_EVIDENCE'


class SemanticNeighbor(BaseModel):
    text: str
    similarity: float = Field(ge=-1, le=1)
    language: str
    category: str


class SemanticNeighbors(BaseModel):
    available: bool = False
    suspicious: list[SemanticNeighbor] = Field(default_factory=list, max_length=2)
    safe: list[SemanticNeighbor] = Field(default_factory=list, max_length=2)


class SourceEvidence(BaseModel):
    available: bool
    contributed: bool = False
    suspicious: bool = False
    safety_warning: bool = False
    signals: list[SignalCode] = Field(default_factory=list)
    score: float | None = None
    score_raised: bool = False


class DeterministicEvidence(SourceEvidence):
    risk_before_fusion: int


class MLEvidence(SourceEvidence):
    model_version: str | None = None
    evidence_level: str
    semantic_neighbors: SemanticNeighbors = Field(default_factory=SemanticNeighbors)


class Agreement(BaseModel):
    status: AgreementStatus
    explanation: str
    suspicious_sources: list[str]
    available_sources: list[str]


class Intelligence(BaseModel):
    deterministic: DeterministicEvidence
    ml: MLEvidence
    llm: SourceEvidence
    agreement: Agreement
