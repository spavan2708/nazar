from typing import Literal

from pydantic import BaseModel, field_validator

from schemas.analysis import TextAnalysisResponse


class InteractionRequest(BaseModel):
    type: Literal["text"]
    content: str

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Content must not be blank")
        return value.strip()


class Interaction(BaseModel):
    interaction_id: str
    type: Literal["text"]
    content: str
    analysis: TextAnalysisResponse


class Campaign(BaseModel):
    campaign_id: str
    campaign_score: int
    risk_level: Literal["low", "medium", "high", "critical"]
    interactions: list[Interaction]
