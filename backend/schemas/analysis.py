from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class SignalCode(StrEnum):
    URGENCY = "URGENCY"
    LINK_REQUEST = "LINK_REQUEST"
    IDENTITY_VERIFICATION = "IDENTITY_VERIFICATION"
    BANK_IMPERSONATION = "BANK_IMPERSONATION"
    GOVERNMENT_IMPERSONATION = "GOVERNMENT_IMPERSONATION"
    OTP_REQUEST = "OTP_REQUEST"
    CREDENTIAL_REQUEST = "CREDENTIAL_REQUEST"
    REMOTE_ACCESS = "REMOTE_ACCESS"
    PAYMENT_REQUEST = "PAYMENT_REQUEST"
    ACCOUNT_THREAT = "ACCOUNT_THREAT"
    INVESTMENT_PROMISE = "INVESTMENT_PROMISE"


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
    signal_codes: set[SignalCode] = Field(default_factory=set, exclude=True)
