from rag.retriever import retrieve_guidance
from uuid import uuid4
from collections.abc import Callable
from dataclasses import dataclass, field
from threading import RLock
import time
from services.limits import MAX_CAMPAIGNS, MAX_EVIDENCE, CAMPAIGN_TTL_SECONDS

from schemas.analysis import SignalCode
from schemas.campaign import Campaign, Interaction, InteractionRequest, InvestigationState
from schemas.evidence import EvidenceDraft, EvidenceType
from services.analysis_service import analyze_text
from services.risk_levels import risk_level_for_score
from services.text_analyzer import SIGNAL_LABELS
from services.investigation_stages import apply_stages


class CampaignNotFoundError(Exception):
    pass


_campaigns: dict[str, Campaign] = {}
_created: dict[str, float] = {}


def _expire():
    now = time.monotonic()
    for key in list(_created):
        if key not in _campaigns or (now - _created[key] >= CAMPAIGN_TTL_SECONDS and not _request_states.get(key, EvidenceRequests()).busy):
            _campaigns.pop(key, None)
            _request_states.pop(key, None)
            _created.pop(key, None)


def create_campaign() -> Campaign:
    campaign = Campaign(
        campaign_id=str(uuid4()),
        campaign_score=0,
        risk_level=risk_level_for_score(0),
        interactions=[],
    )
    with _mutation_lock:
        _expire()
        if len(_campaigns) >= MAX_CAMPAIGNS:
            raise EvidenceConflictError("Investigation capacity reached. Try again after older investigations expire.")
        _campaigns[campaign.campaign_id] = campaign
        _created[campaign.campaign_id] = time.monotonic()
    return campaign.model_copy(deep=True)


def get_campaign(campaign_id: str) -> Campaign:
    with _mutation_lock:
        _expire()
    try:
        return _campaigns[campaign_id]
    except KeyError as error:
        raise CampaignNotFoundError(campaign_id) from error


class EvidenceConflictError(Exception):
    pass


@dataclass
class EvidenceRequests:
    busy: bool = False
    completed: dict[str, str] = field(default_factory=dict)


_request_states: dict[str, EvidenceRequests] = {}
_mutation_lock = RLock()


def add_interaction(campaign_id: str, request: InteractionRequest) -> Campaign:
    # Backward-compatible text endpoint, through the same normalization/commit path.
    return add_evidence(campaign_id, lambda: EvidenceDraft(
        type=EvidenceType.TEXT, content=request.content, analysis=analyze_text(request.content),
    ))


def add_evidence(
    campaign_id: str,
    prepare: Callable[[], EvidenceDraft],
    request_id: str | None = None,
    fingerprint: str = "",
) -> Campaign:
    with _mutation_lock:
        get_campaign(campaign_id)  # Reject expired IDs before expensive processing.
        state = _request_states.setdefault(campaign_id, EvidenceRequests())
        if request_id in state.completed:
            if state.completed[request_id] != fingerprint:
                raise EvidenceConflictError("This submission key was already used for different evidence. Submit with a new key.")
            return get_campaign(campaign_id).model_copy(deep=True)
        if len(get_campaign(campaign_id).interactions) >= MAX_EVIDENCE:
            raise EvidenceConflictError("This investigation has reached 100 evidence items. Start a new investigation.")
        if state.busy:
            raise EvidenceConflictError("Evidence is already being processed for this investigation. Refresh or retry shortly.")
        state.busy = True
    try:
        draft = prepare()
        # Preserve the internal canonical set; dumping/revalidating would lose it.
        analysis = draft.analysis.model_copy(deep=True)
        if analysis.semantic is not None:
            analysis.semantic.provider = None
            analysis.semantic.model_version = None
            analysis.semantic.is_mock = False
        if analysis.intelligence is not None:
            analysis.intelligence.ml.model_version = None
        if analysis.ml is not None:
            analysis.ml.model_version = None
        with _mutation_lock:
            campaign = get_campaign(campaign_id).model_copy(deep=True)
            previous_score = campaign.campaign_score
            item = Interaction(
                interaction_id=str(uuid4()), type=draft.type,
                order=len(campaign.interactions) + 1, content=draft.content,
                display_text=draft.content, extracted_text=draft.extracted_text,
                transcript=draft.transcript, submitted_url=draft.submitted_url,
                analysis=analysis, canonical_signal_codes=sorted(analysis.signal_codes),
                metadata=draft.metadata.model_copy(deep=True),
            )
            # The existing correlation formula runs once, on prepared analyses.
            campaign.campaign_score = _calculate_campaign_score([*campaign.interactions, item])
            campaign.risk_level = risk_level_for_score(campaign.campaign_score)
            item.campaign_score_after = campaign.campaign_score
            item.campaign_risk_level_after = campaign.risk_level
            item.risk_delta = campaign.campaign_score - previous_score
            apply_stages(campaign, item)
            campaign.interactions.append(item)
            campaign.evidence_count = len(campaign.interactions)
            codes = set().union(*(entry.analysis.signal_codes for entry in campaign.interactions))
            campaign.canonical_signal_codes = sorted(codes)
            semantics = [e.analysis.semantic for e in campaign.interactions if e.analysis.semantic and e.analysis.semantic.available]
            campaign.structured_state = InvestigationState(
                claimed_identities=list(dict.fromkeys(s.claimed_identity for s in semantics if s.claimed_identity))[:100],
                requested_actions=list(dict.fromkeys(action for s in semantics for action in s.requested_actions))[:100],
                known_urls=list(dict.fromkeys(u.normalized_url for e in campaign.interactions for u in e.analysis.urls if u.valid and u.normalized_url))[:100],
                established_signals=sorted(codes), established_stages=list(campaign.stages))
            campaign.grounding = retrieve_guidance("", codes, campaign.stages)
            labels = [label.lower() for code, label in SIGNAL_LABELS.items() if code in codes]
            campaign.explanation = (
                "Across this sequence, Nazar found " + ", ".join(labels) + ". Review these related requests together."
                if labels else
                "The score reflects the individual evidence analyses. No canonical scam signals have been reported across this sequence."
            )
            _campaigns[campaign_id] = campaign
            if request_id is not None:
                state.completed[request_id] = fingerprint
            return campaign.model_copy(deep=True)
    finally:
        with _mutation_lock:
            state.busy = False


def _calculate_campaign_score(interactions: list[Interaction]) -> int:
    interaction_scores = [interaction.analysis.score for interaction in interactions]
    highest_score = max(interaction_scores, default=0)
    remaining_scores = sum(interaction_scores) - highest_score
    score = highest_score + round(remaining_scores * 0.20)
    signal_codes = set().union(
        *(interaction.analysis.signal_codes for interaction in interactions)
    )

    if {SignalCode.IDENTITY_VERIFICATION, SignalCode.URGENCY} <= signal_codes:
        score += 5
    if {SignalCode.IDENTITY_VERIFICATION, SignalCode.REMOTE_ACCESS} <= signal_codes:
        score += 10
    if {SignalCode.REMOTE_ACCESS, SignalCode.OTP_REQUEST} <= signal_codes:
        score += 20
    if {SignalCode.PAYMENT_REQUEST, SignalCode.OTP_REQUEST} <= signal_codes:
        score += 20

    elevated_interactions = sum(value >= 35 for value in interaction_scores)
    if elevated_interactions > 1:
        score += (elevated_interactions - 1) * 5

    for index, current_score in enumerate(interaction_scores[1:], start=1):
        if current_score > max(interaction_scores[:index]):
            score += 5

    return min(score, 100)
