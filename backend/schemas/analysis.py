from pydantic import BaseModel, field_validator


class TextAnalysisRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text must not be blank")
        return value.strip()


class TextAnalysisResponse(BaseModel):
    score: int
    risk_level: str
    signals: list[str]
    explanation: str
    recommended_action: str
