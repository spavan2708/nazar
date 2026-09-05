from enum import StrEnum

from pydantic import BaseModel, Field

from schemas.analysis import TextAnalysisResponse
from services.visual_analysis import VisualEvidence


class EvidenceType(StrEnum):
    TEXT = "text"
    SCREENSHOT = "screenshot"
    URL = "url"
    AUDIO = "audio"


class EvidenceMetadata(BaseModel):
    visual: VisualEvidence | None = None
    format: str | None = None
    width: int | None = None
    height: int | None = None
    duration_seconds: float | None = None
    detected_language: str | None = None
    ocr_languages: str | None = None
    partial_ocr: bool = False


class EvidenceDraft(BaseModel):
    """Internal adapter output, never accepted directly from an API client."""
    type: EvidenceType
    content: str
    analysis: TextAnalysisResponse
    extracted_text: str | None = None
    transcript: str | None = None
    submitted_url: str | None = None
    metadata: EvidenceMetadata = Field(default_factory=EvidenceMetadata)
