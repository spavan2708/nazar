import re
import unicodedata

from services.multilingual_patterns import MULTILINGUAL_ACTIONS, MULTILINGUAL_SAFETY, MULTILINGUAL_SIGNALS
from services.sensitive_requests import SENSITIVE_SAFETY, PRESSURE, request_signals, ambiguous_pressure, benign_code_context, safe_clause, clauses as request_clauses
from services.risk_levels import risk_level_for_score
from services.remote_access_patterns import REMOTE_SAFETY, remote_access_request

from schemas.analysis import AnalysisContext, SignalCode, TextAnalysisResponse


SIGNAL_LABELS = {
    SignalCode.URGENCY: "Urgency or pressure",
    SignalCode.LINK_REQUEST: "Request to follow a link",
    SignalCode.IDENTITY_VERIFICATION: "Identity verification pretext",
    SignalCode.BANK_IMPERSONATION: "Bank impersonation",
    SignalCode.GOVERNMENT_IMPERSONATION: "Government impersonation",
    SignalCode.OTP_REQUEST: "OTP request",
    SignalCode.CREDENTIAL_REQUEST: "Credential request",
    SignalCode.REMOTE_ACCESS: "Remote access request",
    SignalCode.PAYMENT_REQUEST: "Payment request",
    SignalCode.ACCOUNT_THREAT: "Account threat",
    SignalCode.INVESTMENT_PROMISE: "Investment promise",
}

SIGNAL_PATTERNS = {
    SignalCode.URGENCY: ("urgent", "immediately", "today", "expires", "act now", "now"),
    SignalCode.LINK_REQUEST: ("click", "link", "http://", "https://"),
    SignalCode.IDENTITY_VERIFICATION: (
        "kyc",
        "verify",
        "verify your identity",
        "account verification",
    ),
    SignalCode.BANK_IMPERSONATION: (
        "your bank",
        "from your bank",
        "bank official",
        "bank agent",
    ),
    SignalCode.GOVERNMENT_IMPERSONATION: (
        "government official",
        "income tax department",
        "police department",
    ),
    SignalCode.OTP_REQUEST: ("otp", "one time password", "one-time password"),
    SignalCode.CREDENTIAL_REQUEST: ("password", "pin", "cvv"),
    SignalCode.REMOTE_ACCESS: (
        "screen sharing",
        "screen-sharing",
        "share your screen",
        "remote access",
        "remote desktop",
        "install support app",
        "install this support application",
        "anydesk",
        "teamviewer",
    ),
    SignalCode.PAYMENT_REQUEST: (
        "transfer money",
        "send money",
        "payment request",
        "pay now",
        "upi payment",
    ),
    SignalCode.ACCOUNT_THREAT: (
        "account will be blocked",
        "suspended",
        "frozen",
        "deactivated",
    ),
    SignalCode.INVESTMENT_PROMISE: (
        "guaranteed returns",
        "double your money",
        "risk-free investment",
    ),
}

SIGNAL_SEVERITY = {
    SignalCode.URGENCY: 35,
    SignalCode.LINK_REQUEST: 35,
    SignalCode.IDENTITY_VERIFICATION: 20,
    SignalCode.BANK_IMPERSONATION: 25,
    SignalCode.GOVERNMENT_IMPERSONATION: 25,
    SignalCode.OTP_REQUEST: 40,
    SignalCode.CREDENTIAL_REQUEST: 40,
    SignalCode.REMOTE_ACCESS: 40,
    SignalCode.PAYMENT_REQUEST: 30,
    SignalCode.ACCOUNT_THREAT: 30,
    SignalCode.INVESTMENT_PROMISE: 30,
}

SAFETY_PHRASES = (
    "do not share",
    "never share",
    "don't share",
    "never reveal",
    "do not install",
    "avoid clicking",
    "beware of",
    "scam warning",
    "fraud alert",
    "do not respond",
    "will never ask",
)

ACTION_VERBS = (
    "send",
    "share",
    "tell",
    "give",
    "provide",
    "install",
    "download",
    "click",
    "transfer",
    "pay",
    "verify",
    "reveal",
)

ACTION_REQUIRED_SIGNALS = {
    SignalCode.LINK_REQUEST,
    SignalCode.IDENTITY_VERIFICATION,
    SignalCode.OTP_REQUEST,
    SignalCode.CREDENTIAL_REQUEST,
    SignalCode.REMOTE_ACCESS,
    SignalCode.PAYMENT_REQUEST,
}

ACTION_CONTEXT_SIGNALS = {
    SignalCode.OTP_REQUEST,
    SignalCode.CREDENTIAL_REQUEST,
    SignalCode.REMOTE_ACCESS,
    SignalCode.PAYMENT_REQUEST,
}

PATTERN_RULES = {
    "coercive_verification": (
        {SignalCode.ACCOUNT_THREAT, SignalCode.IDENTITY_VERIFICATION, SignalCode.URGENCY},
        20,
    ),
    "credential_theft": (
        {SignalCode.CREDENTIAL_REQUEST, SignalCode.URGENCY},
        15,
    ),
    "otp_bank_impersonation": (
        {SignalCode.OTP_REQUEST, SignalCode.BANK_IMPERSONATION},
        20,
    ),
    "remote_takeover_credentials": (
        {SignalCode.REMOTE_ACCESS, SignalCode.CREDENTIAL_REQUEST},
        20,
    ),
    "remote_takeover_otp": (
        {SignalCode.REMOTE_ACCESS, SignalCode.OTP_REQUEST},
        20,
    ),
    "payment_coercion": (
        {SignalCode.PAYMENT_REQUEST, SignalCode.URGENCY},
        15,
    ),
}


def analyze_text(text: str, *, url_evidence: bool = False) -> TextAnalysisResponse:
    normalized_text = _normalize(text)
    context = _detect_context(normalized_text)
    signal_codes = _detect_signals(normalized_text, context)
    if url_evidence and not context.is_safety_warning:
        signal_codes.add(SignalCode.LINK_REQUEST)
    patterns = _detect_combination_patterns(signal_codes)
    score = _calculate_score(signal_codes, context, patterns)
    signals = [
        label for code, label in SIGNAL_LABELS.items() if code in signal_codes
    ]
    risk_level, recommended_action = risk_guidance(score)
    explanation = _build_explanation(signals, context)

    return TextAnalysisResponse(
        score=score,
        risk_level=risk_level,
        signals=signals,
        explanation=explanation,
        recommended_action=recommended_action,
        signal_codes=signal_codes,
        context=context,
        patterns=patterns,
    )


def _normalize(text: str) -> str:
    return re.sub(r"[^\S\n]+", " ", unicodedata.normalize("NFKC", text).lower().replace("’", "'").replace("\u200b", "").replace("\ufeff", "")).strip()


def _contains(text: str, phrase: str) -> bool:
    if phrase.startswith(("http://", "https://")):
        return phrase in text
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text) is not None


def _detect_context(text: str) -> AnalysisContext:
    all_safety = SAFETY_PHRASES + MULTILINGUAL_SAFETY + REMOTE_SAFETY + SENSITIVE_SAFETY
    # Safety belongs to clauses. An exception or another request must not hide
    # behind a warning elsewhere in the input. Preserve original sentence breaks.
    clauses = request_clauses(text)
    safe = [clause for clause in clauses if safe_clause(clause) or any(_contains(clause, phrase) for phrase in all_safety)]
    exceptions = bool(re.search(r"\b(?:except|apart from|unless)\b.{0,45}\b(?:me|us|agent|caller)\b", text))
    remaining = " ".join(clause for clause in clauses if clause not in safe)
    remaining_request = (any(_contains(remaining, verb) for verb in ACTION_VERBS + MULTILINGUAL_ACTIONS)
        or remote_access_request(remaining) or bool(request_signals(text)))
    is_safety_warning = bool(safe) and not exceptions and not remaining_request
    has_action_verb = any(_contains(text, verb) for verb in ACTION_VERBS + MULTILINGUAL_ACTIONS) or remote_access_request(text) or bool(request_signals(text))
    return AnalysisContext(
        is_safety_warning=is_safety_warning,
        is_action_request=has_action_verb and not is_safety_warning,
        has_contextual_pressure=not is_safety_warning and ambiguous_pressure(text),
    )


def _detect_signals(text: str, context: AnalysisContext) -> set[SignalCode]:
    if context.is_safety_warning:
        return set()

    # Exclude warning clauses from evidence attribution when a different clause
    # contains a real request. Exception clauses remain active.
    implicit = request_signals(text)
    phrases = SAFETY_PHRASES + MULTILINGUAL_SAFETY + REMOTE_SAFETY + SENSITIVE_SAFETY
    text = "; ".join(clause for clause in request_clauses(text)
        if not (safe_clause(clause) or any(_contains(clause, phrase) for phrase in phrases))
        or re.search(r"\b(?:except|apart from|unless)\b", clause))
    detected = {
        code
        for code, phrases in SIGNAL_PATTERNS.items()
        if any(_contains(text, phrase) for phrase in phrases)
    }
    detected.update(
        code for code, phrases in MULTILINGUAL_SIGNALS.items()
        if any(_contains(text, phrase) for phrase in phrases)
        and (code != SignalCode.URGENCY or context.is_action_request)
    )
    if remote_access_request(text):
        detected.add(SignalCode.REMOTE_ACCESS)
    detected.update(implicit)
    if benign_code_context(text):
        # Only suppress ambiguous code/PIN concepts, never an explicit OTP elsewhere.
        if not request_signals(text):
            detected.discard(SignalCode.CREDENTIAL_REQUEST)
    if not context.is_action_request:
        detected -= ACTION_REQUIRED_SIGNALS
    if detected - {SignalCode.URGENCY}:
        if context.is_action_request and PRESSURE.search(text):
            detected.add(SignalCode.URGENCY)
    else:
        detected.discard(SignalCode.URGENCY)
    return detected


def _detect_combination_patterns(signal_codes: set[SignalCode]) -> list[str]:
    return [
        name
        for name, (required_signals, _) in PATTERN_RULES.items()
        if required_signals <= signal_codes
    ]


def _calculate_score(
    signal_codes: set[SignalCode],
    context: AnalysisContext,
    patterns: list[str],
) -> int:
    base_severity = sum(SIGNAL_SEVERITY[code] for code in signal_codes)
    context_modifier = (
        5
        if context.is_action_request and signal_codes & ACTION_CONTEXT_SIGNALS
        else 0
    )
    pattern_severity = sum(PATTERN_RULES[name][1] for name in patterns)
    return min(base_severity + context_modifier + pattern_severity, 100)


def risk_guidance(score: int) -> tuple[str, str]:
    level = risk_level_for_score(score)
    # Preserve existing action guidance; only the score-to-label mapping changes.
    if score >= 70:
        return (
            level,
            "Do not click or respond. Verify the request through the official organization.",
        )
    if score >= 35:
        return (
            level,
            "Pause and verify the sender through a trusted channel before acting.",
        )
    return (
        level,
        "No common scam signs were detected, but stay cautious with unexpected requests.",
    )


def _build_explanation(signals: list[str], context: AnalysisContext) -> str:
    if context.is_safety_warning:
        return "The message appears to be safety advice rather than a request to take a risky action."
    if signals:
        detail = (" Verification codes can give access to accounts; do not send them to another person."
            if SIGNAL_LABELS[SignalCode.OTP_REQUEST] in signals else "")
        return "The message contains: " + ", ".join(
            signal.lower() for signal in signals
        ) + "." + detail
    return "No common scam signs were detected by the current rule set."
