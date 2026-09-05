from typing import Literal

from pydantic import BaseModel

from schemas.analysis import TextAnalysisResponse


class AudioMetadata(BaseModel):
    engine: Literal["whisper.cpp"] = "whisper.cpp"
    detected_language: str | None = None
    duration_seconds: float
    format: Literal["wav", "mp3", "m4a", "webm"]


class AudioAnalysisResponse(BaseModel):
    transcript: str
    analysis: TextAnalysisResponse
    audio: AudioMetadata
