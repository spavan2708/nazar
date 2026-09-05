"""Type adapters: analyze exactly once, then hand normalized output to correlation."""
import hashlib

from schemas.evidence import EvidenceDraft, EvidenceMetadata, EvidenceType
from services import analysis_service, audio_analysis, campaign_service, image_analysis
from services.url_intelligence import analyze_url


def add_text(campaign_id: str, text: str, request_id: str | None = None):
    return _submit(campaign_id, EvidenceType.TEXT, text.encode(), request_id,
        lambda: EvidenceDraft(type=EvidenceType.TEXT, content=text, analysis=analysis_service.analyze_text(text)))


def add_url(campaign_id: str, url: str, request_id: str | None = None):
    def prepare():
        structural = analyze_url(url)
        result = analysis_service.analyze_text(url, precomputed_urls=([structural], False))
        return EvidenceDraft(type=EvidenceType.URL, content=structural.normalized_url,
            submitted_url=structural.normalized_url, analysis=result)
    return _submit(campaign_id, EvidenceType.URL, url.encode(), request_id, prepare)


def add_image(campaign_id: str, data: bytes, mime: str | None, request_id: str | None = None):
    def prepare():
        result = image_analysis.analyze_image(data, mime)
        return EvidenceDraft(type=EvidenceType.SCREENSHOT, content=result.extracted_text or result.analysis.original_text or "Decoded QR evidence",
            extracted_text=result.extracted_text, analysis=result.analysis,
            metadata=EvidenceMetadata(visual=result.visual, format=result.ocr.image_format, width=result.ocr.width,
                height=result.ocr.height, ocr_languages=result.ocr.language,
                partial_ocr=bool(result.ocr.missing_languages) or not result.extracted_text))
    return _submit(campaign_id, EvidenceType.SCREENSHOT, data, request_id, prepare, mime)


def add_audio(campaign_id: str, data: bytes, mime: str | None, request_id: str | None = None):
    def prepare():
        result = audio_analysis.analyze_audio(data, mime)
        return EvidenceDraft(type=EvidenceType.AUDIO, content=result.transcript,
            transcript=result.transcript, analysis=result.analysis,
            metadata=EvidenceMetadata(format=result.audio.format, duration_seconds=result.audio.duration_seconds,
                detected_language=result.audio.detected_language))
    return _submit(campaign_id, EvidenceType.AUDIO, data, request_id, prepare, mime)


def _submit(campaign_id, kind, payload, request_id, prepare, mime=None):
    fingerprint = hashlib.sha256(kind.value.encode() + b"\0" + (mime or "").encode() + b"\0" + payload).hexdigest()
    return campaign_service.add_evidence(campaign_id, prepare, request_id, fingerprint)
