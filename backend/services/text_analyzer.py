from schemas.analysis import TextAnalysisResponse


def analyze_text(text: str) -> TextAnalysisResponse:
    normalized_text = text.lower()
    signals = []
    score = 0

    if any(
        term in normalized_text
        for term in ("urgent", "immediately", "today", "expires", "act now")
    ):
        signals.append("Urgency or pressure")
        score += 35

    if any(
        term in normalized_text for term in ("click", "link", "http://", "https://")
    ):
        signals.append("Request to follow a link")
        score += 35

    if any(
        term in normalized_text
        for term in ("kyc", "verify your identity", "account verification")
    ):
        signals.append("Identity verification pretext")
        score += 20

    score = min(score, 100)

    if score >= 70:
        risk_level = "high"
        recommended_action = "Do not click or respond. Verify the request through the official organization."
    elif score >= 35:
        risk_level = "medium"
        recommended_action = "Pause and verify the sender through a trusted channel before acting."
    else:
        risk_level = "low"
        recommended_action = "No common scam signs were detected, but stay cautious with unexpected requests."

    explanation = (
        "The message contains: " + ", ".join(signal.lower() for signal in signals) + "."
        if signals
        else "No common scam signs were detected by the current rule set."
    )

    return TextAnalysisResponse(
        score=score,
        risk_level=risk_level,
        signals=signals,
        explanation=explanation,
        recommended_action=recommended_action,
    )
