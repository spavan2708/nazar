import json

from services.llm.base import SemanticProvider
from services.llm.semantic_analyzer import analyze_semantics_with_diagnostics


SMOKE_TEST_MESSAGE = (
    "Please send me the verification code that just arrived on your phone."
)


def run_smoke_test(provider: SemanticProvider | None = None) -> dict:
    result, diagnostic = analyze_semantics_with_diagnostics(
        SMOKE_TEST_MESSAGE,
        provider,
    )
    safe_result = {
        "available": result.available,
        "risk_score": result.risk_score,
        "intent": result.intent,
        "tactics": result.tactics,
        "requested_actions": result.requested_actions,
        "signals": [signal.model_dump(mode="json") for signal in result.signals],
        "explanation": result.explanation,
        "provider": result.provider,
        "model": result.model_version,
        "is_mock": result.is_mock,
    }
    if diagnostic is not None:
        safe_result["diagnostic"] = diagnostic.as_safe_dict()
    return safe_result


def main() -> int:
    safe_result = run_smoke_test()
    print(json.dumps(safe_result, indent=2))
    if not safe_result["available"]:
        print("Semantic provider is unavailable; check backend LLM configuration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
