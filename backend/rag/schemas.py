from datetime import date
from typing import Literal
from urllib.parse import urlsplit
from pydantic import BaseModel, ConfigDict, Field, field_validator
from schemas.signals import SignalCode
from schemas.stages import ScamStage

TRUSTED_HOSTS = frozenset({
    'www.cert-in.org.in', 'www.csk.gov.in', 'sbi.co.in', 'sbi.bank.in',
    'cyber.delhipolice.gov.in', 'cybercrime.gov.in', 'consumer.ftc.gov',
})
Topic = Literal['otp', 'credentials', 'remote_access', 'banking_kyc', 'phishing',
                'payment_upi', 'account_threat', 'government_impersonation', 'investment', 'recovery']


def trusted_url(value: str) -> str:
    parts = urlsplit(value)
    if (parts.scheme != 'https' or parts.hostname not in TRUSTED_HOSTS
            or parts.username or parts.password or parts.port not in (None, 443)
            or '\\' in value or any(ord(c) < 33 for c in value)):
        raise ValueError('Reference URL must use an approved official HTTPS host')
    return value


class KnowledgeDocument(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    id: str = Field(pattern=r'^[a-z0-9-]{1,80}$')
    title: str = Field(min_length=1, max_length=160)
    source_name: str = Field(min_length=1, max_length=100)
    source_url: str
    published_or_updated: str | None = Field(default=None, max_length=40)
    reviewed_on: date
    source_section: str = Field(min_length=1, max_length=200)
    provenance_note: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=20, max_length=1800)
    topics: list[Topic] = Field(min_length=1, max_length=3)
    signal_codes: list[SignalCode] = Field(default_factory=list, max_length=11)
    _url = field_validator('source_url')(trusted_url)


class KnowledgeChunk(BaseModel):
    model_config = ConfigDict(extra='forbid')
    chunk_id: str
    source_id: str
    text: str = Field(min_length=1, max_length=800)
    topics: list[Topic]
    signal_codes: list[SignalCode]


class GroundingResult(BaseModel):
    source_id: str
    chunk_id: str
    title: str
    source_name: str
    source_url: str
    guidance: str
    topics: list[Topic]
    matched_signals: list[SignalCode] = Field(default_factory=list)
    matched_topics: list[Topic] = Field(default_factory=list)
    matched_stages: list[ScamStage] = Field(default_factory=list)
    similarity: float | None = Field(default=None, ge=-1, le=1)
    reviewed_on: date | None = None
    review_due: bool = False
    relevance: Literal['signal', 'stage', 'topic', 'semantic']
    _url = field_validator('source_url')(trusted_url)


class Grounding(BaseModel):
    available: bool = False
    results: list[GroundingResult] = Field(default_factory=list, max_length=3)
