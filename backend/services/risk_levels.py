from typing import Literal

RiskLevel = Literal["low", "medium", "high", "critical"]


def risk_level_for_score(score: int) -> RiskLevel:
    """Shared display labels, using the existing campaign boundaries.

    This does not calculate scores or alter model/scoring thresholds.
    """
    if score >= 85:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 30:
        return "medium"
    return "low"
