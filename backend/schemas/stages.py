from enum import StrEnum
from pydantic import BaseModel, Field


class ScamStage(StrEnum):
    IMPERSONATION = 'IMPERSONATION'
    URGENCY_OR_PRESSURE = 'URGENCY_OR_PRESSURE'
    VERIFICATION_PRETEXT = 'VERIFICATION_PRETEXT'
    LINK_REDIRECTION = 'LINK_REDIRECTION'
    CREDENTIAL_HARVESTING = 'CREDENTIAL_HARVESTING'
    PAYMENT_EXTRACTION = 'PAYMENT_EXTRACTION'
    REMOTE_ACCESS = 'REMOTE_ACCESS'
    AUTHENTICATION_TAKEOVER = 'AUTHENTICATION_TAKEOVER'
    INVESTMENT_LURE = 'INVESTMENT_LURE'


class StageProgression(BaseModel):
    evidence_id: str
    evidence_order: int
    new_stages: list[ScamStage] = Field(default_factory=list)
    current_stage: ScamStage


class ContextualReinforcement(BaseModel):
    stage: ScamStage
    source_evidence_id: str
    source_evidence_order: int
    explanation: str
