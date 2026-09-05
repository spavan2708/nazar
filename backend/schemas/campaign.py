from rag.schemas import Grounding
from typing import Literal
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator

from schemas.analysis import TextAnalysisResponse
from schemas.evidence import EvidenceMetadata, EvidenceType
from schemas.signals import SignalCode
from schemas.stages import ScamStage, StageProgression, ContextualReinforcement


from services.limits import MAX_TEXT_CHARS


class InteractionRequest(BaseModel):
    type: Literal["text"]
    content: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Content must not be blank")
        return value.strip()


class Interaction(BaseModel):
    interaction_id: str
    type: EvidenceType
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    order: int = 0
    display_text: str = ""
    extracted_text: str | None = None
    transcript: str | None = None
    submitted_url: str | None = None
    canonical_signal_codes: list[SignalCode] = Field(default_factory=list)
    campaign_score_after: int = 0
    campaign_risk_level_after: Literal["low", "medium", "high", "critical"] = "low"
    risk_delta: int = 0
    metadata: EvidenceMetadata = Field(default_factory=EvidenceMetadata)
    stages: list[ScamStage] = Field(default_factory=list)
    new_stages: list[ScamStage] = Field(default_factory=list)
    current_stage_after: ScamStage | None = None
    contextual_reinforcements: list[ContextualReinforcement] = Field(default_factory=list)
    content: str
    analysis: TextAnalysisResponse


class InvestigationState(BaseModel):
    claimed_identities: list[str] = Field(default_factory=list)
    requested_actions: list[str] = Field(default_factory=list)
    known_urls: list[str] = Field(default_factory=list)
    established_signals: list[SignalCode] = Field(default_factory=list)
    established_stages: list[ScamStage] = Field(default_factory=list)
    correlation_method: str = "Structured evidence only; no additional model calls"


class Campaign(BaseModel):
    structured_state: InvestigationState = Field(default_factory=InvestigationState)
    grounding: Grounding | None = None
    campaign_id: str
    campaign_score: int
    risk_level: Literal["low", "medium", "high", "critical"]
    interactions: list[Interaction]
    evidence_count: int = 0
    canonical_signal_codes: list[SignalCode] = Field(default_factory=list)
    explanation: str = "Add related evidence to investigate a suspicious sequence."

    stages: list[ScamStage] = Field(default_factory=list)
    stage_progression: list[StageProgression] = Field(default_factory=list)
    current_stage: ScamStage | None = None
    stage_explanation: str = "Add related evidence to identify supported attack stages."
