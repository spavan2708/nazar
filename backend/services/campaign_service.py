from uuid import uuid4

from schemas.analysis import SignalCode
from schemas.campaign import Campaign, Interaction, InteractionRequest
from services.analysis_service import analyze_text


class CampaignNotFoundError(Exception):
    pass


_campaigns: dict[str, Campaign] = {}


def create_campaign() -> Campaign:
    campaign = Campaign(
        campaign_id=str(uuid4()),
        campaign_score=0,
        risk_level="low",
        interactions=[],
    )
    _campaigns[campaign.campaign_id] = campaign
    return campaign


def get_campaign(campaign_id: str) -> Campaign:
    try:
        return _campaigns[campaign_id]
    except KeyError as error:
        raise CampaignNotFoundError(campaign_id) from error


def add_interaction(campaign_id: str, request: InteractionRequest) -> Campaign:
    campaign = get_campaign(campaign_id)
    interaction = Interaction(
        interaction_id=str(uuid4()),
        type=request.type,
        content=request.content,
        analysis=analyze_text(request.content),
    )
    campaign.interactions.append(interaction)
    campaign.campaign_score = _calculate_campaign_score(campaign.interactions)
    campaign.risk_level = _campaign_risk_level(campaign.campaign_score)
    return campaign


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


def _campaign_risk_level(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 30:
        return "medium"
    return "low"
