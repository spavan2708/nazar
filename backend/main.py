from fastapi import FastAPI, HTTPException, UploadFile, Header
from typing import Annotated
from uuid import UUID

from services import evidence_service
from services.campaign_service import EvidenceConflictError
from fastapi.middleware.cors import CORSMiddleware

from schemas.analysis import TextAnalysisRequest, TextAnalysisResponse
from schemas.campaign import Campaign, InteractionRequest
from services.campaign_service import (
    CampaignNotFoundError,
    add_interaction,
    create_campaign,
    get_campaign,
)
from services.analysis_service import analyze_text as analyze_text_content


from schemas.url import URLAnalysisRequest, URLAnalysis
from services.url_intelligence import InvalidURL, analyze_url
from schemas.audio import AudioAnalysisResponse
from services.audio_analysis import MAX_AUDIO_BYTES, AudioAnalysisError, analyze_audio
from services.audio_upload_limit import AudioUploadLimitMiddleware
from schemas.image import ImageAnalysisResponse
from services.image_analysis import MAX_IMAGE_BYTES, ImageAnalysisError, analyze_image
from services.image_upload_limit import ImageUploadLimitMiddleware


from services.request_limits import JSONBodyLimitMiddleware

app = FastAPI()
app.add_middleware(JSONBodyLimitMiddleware)
app.add_middleware(ImageUploadLimitMiddleware)
app.add_middleware(AudioUploadLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Idempotency-Key"],
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


@app.post("/api/analyze/url", response_model=URLAnalysis)
def analyze_link(request: URLAnalysisRequest):
    try:
        return analyze_url(request.url)
    except InvalidURL as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@app.post("/api/analyze/image", response_model=ImageAnalysisResponse)
def analyze_screenshot(file: UploadFile):
    try:
        return analyze_image(file.file.read(MAX_IMAGE_BYTES + 1), file.content_type)
    except ImageAnalysisError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from None
    finally:
        file.file.close()


@app.post("/api/analyze/audio", response_model=AudioAnalysisResponse)
def analyze_recording(file: UploadFile):
    try:
        return analyze_audio(file.file.read(MAX_AUDIO_BYTES + 1), file.content_type)
    except AudioAnalysisError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from None
    finally:
        file.file.close()


@app.post("/api/campaigns", response_model=Campaign)
def create_campaign_route():
    try:
        return create_campaign()
    except EvidenceConflictError as error:
        raise HTTPException(status_code=429, detail=str(error)) from None


@app.post("/api/campaigns/{campaign_id}/interactions", response_model=Campaign)
def add_campaign_interaction(campaign_id: str, request: InteractionRequest):
    try:
        return add_interaction(campaign_id, request)
    except EvidenceConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except CampaignNotFoundError as error:
        raise HTTPException(status_code=404, detail="Campaign not found") from error


@app.get("/api/campaigns/{campaign_id}", response_model=Campaign)
def retrieve_campaign(campaign_id: str):
    try:
        return get_campaign(campaign_id)
    except CampaignNotFoundError as error:
        raise HTTPException(status_code=404, detail="Campaign not found") from error


# Typed JSON and multipart adapters share a single prepared-evidence commit path.
def _evidence_response(action):
    try:
        return action()
    except CampaignNotFoundError:
        raise HTTPException(status_code=404, detail="Investigation not found. It may have expired after a backend restart.") from None
    except EvidenceConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except (ImageAnalysisError, AudioAnalysisError) as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from None
    except InvalidURL as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@app.post("/api/campaigns/{campaign_id}/evidence/text", response_model=Campaign)
def add_text_evidence(campaign_id: str, request: TextAnalysisRequest,
    idempotency_key: Annotated[UUID | None, Header()] = None):
    return _evidence_response(lambda: evidence_service.add_text(campaign_id, request.text,
        str(idempotency_key) if idempotency_key else None))


@app.post("/api/campaigns/{campaign_id}/evidence/url", response_model=Campaign)
def add_url_evidence(campaign_id: str, request: URLAnalysisRequest,
    idempotency_key: Annotated[UUID | None, Header()] = None):
    return _evidence_response(lambda: evidence_service.add_url(campaign_id, request.url,
        str(idempotency_key) if idempotency_key else None))


def _uploaded_evidence(campaign_id, file, limit, adapter, idempotency_key):
    def prepare():
        get_campaign(campaign_id)
        return adapter(campaign_id, file.file.read(limit + 1), file.content_type,
            str(idempotency_key) if idempotency_key else None)
    try:
        return _evidence_response(prepare)
    finally:
        file.file.close()


@app.post("/api/campaigns/{campaign_id}/evidence/image", response_model=Campaign)
def add_image_evidence(campaign_id: str, file: UploadFile,
    idempotency_key: Annotated[UUID | None, Header()] = None):
    return _uploaded_evidence(campaign_id, file, MAX_IMAGE_BYTES, evidence_service.add_image, idempotency_key)


@app.post("/api/campaigns/{campaign_id}/evidence/audio", response_model=Campaign)
def add_audio_evidence(campaign_id: str, file: UploadFile,
    idempotency_key: Annotated[UUID | None, Header()] = None):
    return _uploaded_evidence(campaign_id, file, MAX_AUDIO_BYTES, evidence_service.add_audio, idempotency_key)
