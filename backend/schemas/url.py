from typing import Literal

from pydantic import BaseModel, Field


class URLAnalysisRequest(BaseModel):
    url: str = Field(min_length=1, max_length=4096)


class URLIndicator(BaseModel):
    code: str
    description: str


class URLAnalysis(BaseModel):
    normalized_url: str | None = None
    hostname: str | None = None
    unicode_hostname: str | None = None
    domain: str | None = None
    scheme: str | None = None
    scheme_assumed: bool = False
    port: int | None = None
    path_length: int = 0
    query_parameter_count: int = 0
    query_length: int = 0
    indicators: list[URLIndicator] = Field(default_factory=list)
    structural_risk_score: int | None = None
    risk_level: Literal["low", "medium", "high", "critical"] | None = None
    explanation: str
    valid: bool = True
    evidence_groups: int = Field(default=0, exclude=True)
