"""Explanation-only stage derivation. No text parsing, inference calls or scoring."""
from schemas.analysis import TextAnalysisResponse
from schemas.signals import SignalCode
from schemas.stages import ScamStage, StageProgression, ContextualReinforcement
from schemas.campaign import Campaign, Interaction

# Stable ordering breaks ties within one evidence item; it is not an inferred
# chronology within a message or an additional severity ranking.
SIGNAL_STAGES = {
    SignalCode.BANK_IMPERSONATION: ScamStage.IMPERSONATION,
    SignalCode.GOVERNMENT_IMPERSONATION: ScamStage.IMPERSONATION,
    SignalCode.URGENCY: ScamStage.URGENCY_OR_PRESSURE,
    SignalCode.ACCOUNT_THREAT: ScamStage.URGENCY_OR_PRESSURE,
    SignalCode.IDENTITY_VERIFICATION: ScamStage.VERIFICATION_PRETEXT,
    SignalCode.LINK_REQUEST: ScamStage.LINK_REDIRECTION,
    SignalCode.CREDENTIAL_REQUEST: ScamStage.CREDENTIAL_HARVESTING,
    SignalCode.PAYMENT_REQUEST: ScamStage.PAYMENT_EXTRACTION,
    SignalCode.REMOTE_ACCESS: ScamStage.REMOTE_ACCESS,
    SignalCode.OTP_REQUEST: ScamStage.AUTHENTICATION_TAKEOVER,
    SignalCode.INVESTMENT_PROMISE: ScamStage.INVESTMENT_LURE,
}
STAGE_LABELS = {
    ScamStage.IMPERSONATION: 'impersonation',
    ScamStage.URGENCY_OR_PRESSURE: 'urgency or pressure',
    ScamStage.VERIFICATION_PRETEXT: 'a verification pretext',
    ScamStage.LINK_REDIRECTION: 'link redirection',
    ScamStage.CREDENTIAL_HARVESTING: 'credential harvesting',
    ScamStage.PAYMENT_EXTRACTION: 'payment extraction',
    ScamStage.REMOTE_ACCESS: 'remote access',
    ScamStage.AUTHENTICATION_TAKEOVER: 'authentication takeover',
    ScamStage.INVESTMENT_LURE: 'an investment lure',
}
# One representative label for the latest evidence, never a score or a claim
# that a takeover succeeded. All supporting stages are retained separately.
PRIMARY_ORDER = (
    ScamStage.AUTHENTICATION_TAKEOVER, ScamStage.REMOTE_ACCESS,
    ScamStage.CREDENTIAL_HARVESTING, ScamStage.PAYMENT_EXTRACTION,
    ScamStage.LINK_REDIRECTION, ScamStage.IMPERSONATION,
    ScamStage.VERIFICATION_PRETEXT, ScamStage.INVESTMENT_LURE,
    ScamStage.URGENCY_OR_PRESSURE,
)


def derive_stages(analysis: TextAnalysisResponse) -> list[ScamStage]:
    if analysis.context.is_safety_warning:
        return []
    return list(dict.fromkeys(stage for code, stage in SIGNAL_STAGES.items()
                             if code in analysis.signal_codes))


def apply_stages(campaign: Campaign, item: Interaction) -> None:
    item.stages = derive_stages(item.analysis)
    # The analyzer computed this cue on this message alone. Prior evidence supplies
    # only a cited explanation, never new canonical signals, stages or score.
    if item.analysis.context.has_contextual_pressure and not item.stages:
        previous = campaign.interactions[-1] if campaign.interactions else None
        sensitive = {ScamStage.AUTHENTICATION_TAKEOVER, ScamStage.CREDENTIAL_HARVESTING}
        if previous:
            for stage in previous.stages:
                if stage in sensitive:
                    item.contextual_reinforcements.append(ContextualReinforcement(
                        stage=stage, source_evidence_id=previous.interaction_id,
                        source_evidence_order=previous.order,
                        explanation=f'This ambiguous time-pressure wording may reinforce the {STAGE_LABELS[stage]} request in evidence {previous.order}. No new sensitive request was identified in this evidence.',
                    ))
    item.new_stages = [stage for stage in item.stages if stage not in campaign.stages]
    if item.stages:
        campaign.current_stage = next(stage for stage in PRIMARY_ORDER if stage in item.stages)
    item.current_stage_after = campaign.current_stage
    campaign.stages.extend(item.new_stages)
    if item.new_stages:
        campaign.stage_progression.append(StageProgression(
            evidence_id=item.interaction_id, evidence_order=item.order,
            new_stages=item.new_stages, current_stage=campaign.current_stage,
        ))
    if not campaign.stage_progression:
        campaign.stage_explanation = 'No supported attack stages have been detected. This does not establish that the sequence is safe.'
        return
    steps = [' and '.join(STAGE_LABELS[stage] for stage in step.new_stages)
             for step in campaign.stage_progression]
    # Concise summary remains bounded even in a long investigation (nine unique stages).
    campaign.stage_explanation = (
        'The evidence is consistent with ' + steps[0] + '.' if len(steps) == 1 else
        'The sequence appears to progress from ' + steps[0] + ', then '
        + ', then '.join(steps[1:]) + '.'
    ) + ' These are request patterns, not confirmation that access or payment occurred.'
