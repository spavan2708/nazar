from pydantic import BaseModel, Field

from schemas.signals import SignalCode


class SemanticSignal(BaseModel):
    code: SignalCode
    confidence: float = Field(ge=0.0, le=1.0)


class SemanticProviderOutput(BaseModel):
    risk_score: float = Field(ge=0.0, le=1.0)
    intent: str | None = None
    tactics: list[str] = Field(default_factory=list)
    requested_actions: list[str] = Field(default_factory=list)
    claimed_identity: str | None = None
    signals: list[SemanticSignal] = Field(default_factory=list)
    is_safety_warning: bool = False
    explanation: str


class SemanticAnalysis(BaseModel):
    available: bool
    risk_score: float | None = Field(default=None, ge=0.0, le=1.0)
    intent: str | None = None
    tactics: list[str] = Field(default_factory=list)
    requested_actions: list[str] = Field(default_factory=list)
    claimed_identity: str | None = None
    signals: list[SemanticSignal] = Field(default_factory=list)
    is_safety_warning: bool | None = None
    explanation: str | None = None
    model_version: str | None = None
    provider: str | None = None
    is_mock: bool = False
