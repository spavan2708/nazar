from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator


class TextAnalysisRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text must not be blank")
        return value.strip()


class TextAnalysisResponse(BaseModel):
    score: int
    risk_level: str
    signals: list[str]
    explanation: str
    recommended_action: str


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/")
def read_root():
    return {"message": "Nazar API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/api/analyze/text", response_model=TextAnalysisResponse)
def analyze_text(request: TextAnalysisRequest):
    text = request.text.lower()
    signals = []
    score = 0

    if any(term in text for term in ("urgent", "immediately", "today", "expires", "act now")):
        signals.append("Urgency or pressure")
        score += 35

    if any(term in text for term in ("click", "link", "http://", "https://")):
        signals.append("Request to follow a link")
        score += 35

    if any(term in text for term in ("kyc", "verify your identity", "account verification")):
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
