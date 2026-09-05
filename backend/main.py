from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from schemas.analysis import TextAnalysisRequest, TextAnalysisResponse
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
