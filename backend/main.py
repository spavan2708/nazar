from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from schemas.analysis import TextAnalysisRequest, TextAnalysisResponse
from schemas.campaign import Campaign, InteractionRequest
from services.campaign_service import (
    CampaignNotFoundError,
    add_interaction,
    create_campaign,
    get_campaign,
)
from services.text_analyzer import analyze_text as analyze_text_content


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
    return analyze_text_content(request.text)


@app.post("/api/campaigns", response_model=Campaign)
def create_campaign_route():
    return create_campaign()


@app.post("/api/campaigns/{campaign_id}/interactions", response_model=Campaign)
def add_campaign_interaction(campaign_id: str, request: InteractionRequest):
    try:
        return add_interaction(campaign_id, request)
    except CampaignNotFoundError as error:
        raise HTTPException(status_code=404, detail="Campaign not found") from error


@app.get("/api/campaigns/{campaign_id}", response_model=Campaign)
def retrieve_campaign(campaign_id: str):
    try:
        return get_campaign(campaign_id)
    except CampaignNotFoundError as error:
        raise HTTPException(status_code=404, detail="Campaign not found") from error
