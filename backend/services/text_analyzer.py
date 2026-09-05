from schemas.analysis import SignalCode, TextAnalysisResponse


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
    SignalCode.URGENCY: (
        "urgent",
        "immediately",
        "today",
        "expires",
        "act now",
        "transfer money now",
    ),
    SignalCode.LINK_REQUEST: ("click", "link", "http://", "https://"),
    SignalCode.IDENTITY_VERIFICATION: (
        "kyc",
        "verify your identity",
        "account verification",
    ),
    SignalCode.BANK_IMPERSONATION: ("from your bank", "bank official", "bank agent"),
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

SIGNAL_SCORES = {
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


def analyze_text(text: str) -> TextAnalysisResponse:
    normalized_text = text.lower()
    signal_codes = {
        code
        for code, patterns in SIGNAL_PATTERNS.items()
        if any(pattern in normalized_text for pattern in patterns)
    }
    signals = [
        label for code, label in SIGNAL_LABELS.items() if code in signal_codes
    ]
    score = min(sum(SIGNAL_SCORES[code] for code in signal_codes), 100)

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
        signal_codes=signal_codes,
    )
