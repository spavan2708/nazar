from typing import Literal

from pydantic import BaseModel, Field

from schemas.analysis import TextAnalysisResponse
from services.visual_analysis import VisualEvidence


class OCRMetadata(BaseModel):
    engine: Literal["tesseract"] = "tesseract"
    language: str = "eng"
    requested_languages: list[str] = Field(default_factory=list)
    available_languages: list[str] = Field(default_factory=list)
    missing_languages: list[str] = Field(default_factory=list)
    setup_message: str | None = None
    image_format: Literal["PNG", "JPEG", "WEBP"]
    width: int
    height: int


class ImageAnalysisResponse(BaseModel):
    extracted_text: str
    analysis: TextAnalysisResponse
    ocr: OCRMetadata
    visual: VisualEvidence = Field(default_factory=VisualEvidence)
