import io
import os
import subprocess
import unicodedata
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from schemas.image import ImageAnalysisResponse, OCRMetadata
from services import analysis_service
from services.limits import MAX_TEXT_CHARS
from services.visual_analysis import analyze_visual
from services.orchestration import AgentFinding, describe
from services.url_intelligence import extract_url_analysis
from schemas.analysis import TextAnalysisResponse

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
OCR_TIMEOUT_SECONDS = 20
MIME_FORMATS = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}


class ImageAnalysisError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


def ocr_configuration() -> dict:
    requested = list(dict.fromkeys(os.environ.get("OCR_LANGUAGES", "eng+hin+tam").strip().split("+")))
    if not requested or any(lang not in {"eng", "hin", "tam"} for lang in requested):
        raise ImageAnalysisError(503, "OCR_LANGUAGES must contain eng, hin or tam joined with +.")
    try:
        result = subprocess.run(["tesseract", "--list-langs"], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=5, check=True)
        installed = set(result.stdout.decode("utf-8").splitlines())
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise ImageAnalysisError(503, "Screenshot text extraction is unavailable. Install Tesseract and its language packs, or paste the text instead.") from None
    available = [lang for lang in ("eng", "hin", "tam") if lang in installed]
    selected = [lang for lang in requested if lang in installed]
    missing = [lang for lang in requested if lang not in installed]
    if not selected and "eng" in available:
        selected = ["eng"]
    if not selected:
        raise ImageAnalysisError(503, "No supported OCR language packs are installed. On macOS run brew install tesseract tesseract-lang, or paste the text instead.")
    setup_message = None
    if missing:
        setup_message = (
            "Some screenshot languages are unavailable: " + ", ".join(missing)
            + ". Only installed languages were read. On macOS run brew install tesseract-lang and retry; review the extracted text carefully."
        )
    return dict(language="+".join(selected), requested_languages=requested,
        available_languages=available, missing_languages=missing, setup_message=setup_message)


def extract_text(image: Image.Image, languages: str = "eng") -> str:
    """Run local OCR with in-memory pipes; never persist the upload or log text."""
    encoded = io.BytesIO()
    image.save(encoded, format="PNG")
    try:
        result = subprocess.run(
            ["tesseract", "stdin", "stdout", "-l", languages, "--psm", "11"],
            input=encoded.getvalue(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=OCR_TIMEOUT_SECONDS, check=True,
        )
        return result.stdout.decode("utf-8")
    except FileNotFoundError:
        raise ImageAnalysisError(503, "Screenshot text extraction is unavailable. Paste the message as text instead.") from None
    except (subprocess.SubprocessError, OSError, UnicodeError):
        raise ImageAnalysisError(503, "Could not extract text from this screenshot. Try a clearer image or paste the text instead.") from None


def normalize_text(text: str) -> str:
    # Preserve case, punctuation, words and line order; normalize only Unicode
    # composition, line endings and OCR whitespace (including page breaks).
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n")
    return "\n".join(line for raw in text.split("\n") if (line := " ".join(raw.split())))


def analyze_image(data: bytes, content_type: str | None) -> ImageAnalysisResponse:
    if len(data) > MAX_IMAGE_BYTES:
        raise ImageAnalysisError(413, "Screenshot is too large. Choose an image up to 5 MiB.")
    if content_type not in MIME_FORMATS:
        raise ImageAnalysisError(415, "Choose a PNG, JPEG or WEBP screenshot.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                image_format = source.format
                if image_format != MIME_FORMATS[content_type]:
                    raise ImageAnalysisError(415, "The image format does not match its file type. Choose a PNG, JPEG or WEBP screenshot.")
                if source.width * source.height > MAX_IMAGE_PIXELS:
                    raise ImageAnalysisError(413, "Image dimensions are too large. Choose a screenshot under 16 megapixels.")
                if getattr(source, "is_animated", False):
                    raise ImageAnalysisError(422, "Choose a still screenshot rather than an animated image.")
                source.verify()
            with Image.open(io.BytesIO(data)) as source:
                source.load()
                oriented = ImageOps.exif_transpose(source).convert("RGBA")
                # Flatten transparency on white so text does not disappear.
                background = Image.new("RGBA", oriented.size, "white")
                image = Image.alpha_composite(background, oriented).convert("RGB")
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ImageAnalysisError(413, "Image dimensions are too large. Choose a smaller screenshot.") from None
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise ImageAnalysisError(422, "This image is invalid or damaged. Choose another screenshot.") from None

    with image:
        visual = analyze_visual(image)
        try:
            configuration = ocr_configuration()
            extracted_text = normalize_text(extract_text(image, configuration["language"]))
        except ImageAnalysisError:
            if not any(q.kind in ("url", "payment") for q in visual.qr_codes):
                raise
            configuration = {"language": "", "setup_message": "Text extraction was unavailable. This result only covers decoded QR content."}
            extracted_text = ""
        metadata = OCRMetadata(image_format=image_format, width=image.width, height=image.height, **configuration)
    qr_urls = [q.url for q in visual.qr_codes if q.url is not None]
    analysis_text = extracted_text or "\n".join(u.normalized_url for u in qr_urls)
    if len(analysis_text) > MAX_TEXT_CHARS:
        raise ImageAnalysisError(413, "Extracted content is too long. Crop the screenshot or paste a shorter passage.")
    if analysis_text:
        text_urls, truncated = extract_url_analysis(extracted_text)
        known = {u.normalized_url for u in text_urls}
        combined = text_urls + [u for u in qr_urls if u.normalized_url not in known]
        analysis = (analysis_service.analyze_text(analysis_text, precomputed_urls=(combined[:20], truncated or len(combined)>20))
            if qr_urls else analysis_service.analyze_text(analysis_text))
    elif any(q.kind == "payment" for q in visual.qr_codes):
        # Payment metadata is not a message. Never classify our own helper copy
        # or infer fraud from the presence of a QR payment instruction.
        analysis = TextAnalysisResponse(score=0, risk_level="low", signals=[],
            explanation="A payment QR was decoded, but no readable message was available to assess intent. This does not verify the recipient.",
            recommended_action="Confirm the recipient and amount through a trusted channel before authorizing any payment.")
        analysis.orchestration = describe(analysis)
    else:
        raise ImageAnalysisError(422, "No readable text or supported QR content was found. Try a clearer screenshot or paste the text instead." + (" " + metadata.setup_message if metadata.setup_message else ""))
    if analysis.orchestration:
        analysis.orchestration.findings.append(AgentFinding(agent="visual_evidence", sources=["ocr", "qr"], explanation=visual.limitation))
    return ImageAnalysisResponse(
        visual=visual,
        extracted_text=extracted_text,
        analysis=analysis,
        ocr=metadata,
    )
