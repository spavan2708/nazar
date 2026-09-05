from typing import Literal

from pydantic import BaseModel


class LanguageMetadata(BaseModel):
    detected_language: Literal["English", "Hindi", "Tamil", "Hinglish", "Tanglish", "Mixed", "Unknown"] = "Unknown"
    detected_script: Literal["Latin", "Devanagari", "Tamil", "Mixed", "Other", "Unknown"] = "Unknown"
    is_mixed_language: bool = False
    language_confidence: Literal["low", "medium"] = "low"
    language_detection_method: Literal["script_and_lexical_heuristic"] = "script_and_lexical_heuristic"
