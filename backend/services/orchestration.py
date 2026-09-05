"""Typed, bounded analysis-only specialists. No tools, recursion or model calls.

Specialists project existing findings, so correlated signals never count twice.
The orchestrator invokes only relevant roles and cannot change fusion scores.
"""
from typing import Literal
from pydantic import BaseModel,Field
from schemas.signals import SignalCode

class DetectorEvidence(BaseModel):
    source: str
    available: bool
    score: float | None = None
    confidence_type: Literal['severity','classifier_output','semantic_evidence','structural','reference','derived']
    signals: list[SignalCode] = Field(default_factory=list)
    safety_context: bool = False
    explanation: str

class AgentFinding(BaseModel):
    agent: str
    sources: list[str]
    signals: list[SignalCode] = Field(default_factory=list)
    explanation: str
    determines_risk: bool = False

class Orchestration(BaseModel):
    detectors: list[DetectorEvidence]
    findings: list[AgentFinding] = Field(max_length=12)
    llm_synthesis_calls: int = 0

SPECIALISTS={
    'identity':{SignalCode.BANK_IMPERSONATION,SignalCode.GOVERNMENT_IMPERSONATION},
    'social_engineering':{SignalCode.URGENCY,SignalCode.ACCOUNT_THREAT,SignalCode.IDENTITY_VERIFICATION},
    'credential_theft':{SignalCode.OTP_REQUEST,SignalCode.CREDENTIAL_REQUEST,SignalCode.REMOTE_ACCESS},
    'payment':{SignalCode.PAYMENT_REQUEST,SignalCode.INVESTMENT_PROMISE},
}

def describe(result):
    i=result.intelligence;detectors=[];findings=[]
    if i:
        for source,item,kind in [('rules',i.deterministic,'severity'),('ml',i.ml,'classifier_output'),('llm',i.llm,'semantic_evidence')]:
            detectors.append(DetectorEvidence(source=source,available=item.available,
                score=i.deterministic.risk_before_fusion if source=='rules' else item.score,
                confidence_type=kind,signals=item.signals,safety_context=item.safety_warning,
                explanation='Existing detector evidence; scores have different meanings and are not averaged.'))
        findings.append(AgentFinding(agent='text_threat',sources=['rules','ml','llm'],signals=sorted(result.signal_codes),explanation=result.explanation))
        for name,codes in SPECIALISTS.items():
            found=sorted(result.signal_codes & codes)
            if found:findings.append(AgentFinding(agent=name,sources=['text_threat'],signals=found,explanation='Attributed existing signals; no additional score or inference.'))
        if any(d.safety_context for d in detectors) or i.agreement.status=='CONFLICTING':
            findings.append(AgentFinding(agent='safety_contradiction',sources=['rules','ml','llm'],explanation=i.agreement.explanation))
    for index, url in enumerate(result.urls):
        detectors.append(DetectorEvidence(source=f"url_{index}", available=url.valid, score=url.structural_risk_score, confidence_type="structural", explanation=url.explanation))
    if result.grounding:
        detectors.append(DetectorEvidence(source="rag", available=result.grounding.available, confidence_type="reference", explanation="Topic references are not detector evidence."))
    if result.urls:
        findings.append(AgentFinding(agent='phishing',sources=['offline_url'],explanation='URL structure only; no destination was visited.'))
    if result.grounding and result.grounding.available:
        findings.append(AgentFinding(agent='trusted_guidance',sources=['rag'],explanation='Official topic references only; does not determine risk.'))
    findings.append(AgentFinding(agent='explanation',sources=['fused_evidence'],explanation=result.explanation))
    return Orchestration(detectors=detectors,findings=findings)
