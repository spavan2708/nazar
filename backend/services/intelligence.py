"""Descriptive source agreement only. Never feeds back into risk fusion."""
from schemas.intelligence import (Agreement, AgreementStatus as Status, DeterministicEvidence,
    MLEvidence, SourceEvidence, Intelligence)


def describe_sources(deterministic, ml, llm, *, ml_raised=False, llm_raised=False):
    # Read existing constants rather than creating new evidence thresholds.
    from services.risk_fusion import ML_MODERATE_THRESHOLD, ML_HIGH_THRESHOLD, SEMANTIC_ELEVATED_THRESHOLD, SEMANTIC_SIGNAL_CONFIDENCE
    rules_suspicious = bool(deterministic.signal_codes) and not deterministic.context.is_safety_warning
    ml_suspicious = ml.available and ml.scam_probability is not None and ml.scam_probability >= ML_MODERATE_THRESHOLD
    accepted = sorted({signal.code for signal in llm.signals if signal.confidence >= SEMANTIC_SIGNAL_CONFIDENCE}) if llm.available and not llm.is_safety_warning else []
    llm_suspicious = llm.available and not llm.is_safety_warning and (bool(accepted) or (llm.risk_score is not None and llm.risk_score >= SEMANTIC_ELEVATED_THRESHOLD))
    rules = DeterministicEvidence(available=True, suspicious=rules_suspicious, contributed=rules_suspicious,
        safety_warning=deterministic.context.is_safety_warning, signals=sorted(deterministic.signal_codes), risk_before_fusion=deterministic.score)
    local = MLEvidence(available=ml.available, suspicious=ml_suspicious, contributed=ml_suspicious,
        model_version=ml.model_version, score=ml.scam_probability if ml.available else None,
        evidence_level='unavailable' if not ml.available or ml.scam_probability is None else 'high' if ml.scam_probability >= ML_HIGH_THRESHOLD else 'moderate' if ml_suspicious else 'below_threshold',
        score_raised=ml_raised, semantic_neighbors=ml.semantic_neighbors)
    semantic = SourceEvidence(available=llm.available, suspicious=bool(llm_suspicious), contributed=bool(llm_suspicious),
        safety_warning=bool(llm.available and llm.is_safety_warning), signals=accepted,
        score=llm.risk_score if llm.available else None, score_raised=llm_raised)
    sources={'rules':rules,'ml':local,'llm':semantic}
    suspicious=[name for name,value in sources.items() if value.suspicious]
    available=[name for name,value in sources.items() if value.available]
    if suspicious and any(value.safety_warning for value in sources.values()):
        status=Status.CONFLICTING
        explanation='Analysis sources disagree: safety-warning language was detected, while another source found suspicious evidence. Ambiguous wording and safety examples can lead detectors to disagree.'
    elif len(suspicious)==3:
        status=Status.STRONG_AGREEMENT
        explanation='All three sources found suspicious evidence. This does not confirm fraud.'
    elif len(suspicious)==2:
        status=Status.PARTIAL_AGREEMENT
        explanation='Two sources found suspicious evidence; the remaining source was unavailable or below its evidence threshold.'
    elif len(suspicious)==1:
        status={'rules':Status.RULES_ONLY,'ml':Status.ML_ONLY,'llm':Status.LLM_ONLY}[suspicious[0]]
        explanation='Only one source found suspicious evidence. Other available sources did not; unavailable sources cannot provide confirmation.'
    else:
        status=Status.INSUFFICIENT_EVIDENCE
        explanation='No source supplied suspicious evidence at its existing threshold. This is not a guarantee of safety.'
    return Intelligence(deterministic=rules,ml=local,llm=semantic,
        agreement=Agreement(status=status,explanation=explanation,suspicious_sources=suspicious,available_sources=available))
