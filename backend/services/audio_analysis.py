"""Local speech-to-text input adapter. No scam scoring or remote transcription."""
import array
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import unicodedata
import wave

from schemas.audio import AudioAnalysisResponse, AudioMetadata
from services import analysis_service
from services.limits import MAX_TEXT_CHARS
from services.orchestration import AgentFinding

MAX_AUDIO_BYTES = 20 * 1024 * 1024
MAX_DURATION_SECONDS = 120
SAMPLE_RATE = 16000
BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = BACKEND_DIR / "stt" / "models" / "ggml-base.bin"
TRANSCRIPTION_SLOT = threading.BoundedSemaphore(1)
MIME_FORMATS = {
    "audio/wav": "wav", "audio/x-wav": "wav", "audio/wave": "wav",
    "audio/vnd.wave": "wav", "audio/mpeg": "mp3", "audio/mp3": "mp3",
    "audio/mp4": "m4a", "audio/x-m4a": "m4a", "audio/m4a": "m4a",
    "audio/webm": "webm", "video/webm": "webm",
}
DEMUXERS = {"wav": "wav", "mp3": "mp3", "m4a": "mov", "webm": "matroska"}


class AudioAnalysisError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


def validate_upload(data: bytes, content_type: str | None) -> str:
    if len(data) > MAX_AUDIO_BYTES:
        raise AudioAnalysisError(413, "Recording is too large. Choose a file up to 20 MiB.")
    mime = (content_type or "").split(";", 1)[0].strip().lower()
    if mime not in MIME_FORMATS:
        raise AudioAnalysisError(415, "Choose a WAV, MP3, M4A or WEBM audio recording.")
    format_name = MIME_FORMATS[mime]
    signatures = {
        "wav": len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE",
        "mp3": data.startswith(b"ID3") or (len(data) >= 2 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0),
        "m4a": len(data) >= 12 and data[4:8] == b"ftyp",
        "webm": data.startswith(b"\x1a\x45\xdf\xa3"),
    }
    if not signatures[format_name]:
        raise AudioAnalysisError(422, "The recording is empty, damaged, or does not match its audio type.")
    return format_name


def _input_options(format_name: str) -> list[str]:
    # Force an allowlisted demuxer so uploads cannot become playlists. Only the
    # generated local file/pipe protocols are allowed; MOV external refs disabled.
    options = ["-protocol_whitelist", "file,pipe", "-f", DEMUXERS[format_name]]
    if format_name == "m4a":
        options += ["-enable_drefs", "0", "-use_absolute_path", "0"]
    return options


def decode_audio(source: Path, format_name: str) -> tuple[bytes, float]:
    try:
        probe = subprocess.run([
            "ffprobe", "-v", "error", "-probesize", "5242880", "-analyzeduration", "5000000",
            *_input_options(format_name), "-show_entries", "format=duration:stream=codec_type,duration",
            "-of", "json", str(source),
        ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15, check=True)
        metadata = json.loads(probe.stdout)
        streams = metadata.get("streams", [])
        if not any(stream.get("codec_type") == "audio" for stream in streams):
            raise AudioAnalysisError(422, "No audio track was found in this recording.")
        for entry in [metadata.get("format", {}), *streams]:
            duration = entry.get("duration")
            if duration not in (None, "N/A") and float(duration) > MAX_DURATION_SECONDS:
                raise AudioAnalysisError(413, "Choose a recording no longer than two minutes.")
        decoded = subprocess.run([
            "ffmpeg", "-v", "error", "-nostdin", "-threads", "1", *_input_options(format_name),
            "-i", str(source), "-map", "0:a:0", "-vn", "-sn", "-dn", "-t", str(MAX_DURATION_SECONDS + 1),
            "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "-threads", "1", "pipe:1",
        ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=30, check=True)
    except FileNotFoundError:
        raise AudioAnalysisError(503, "Audio decoding is unavailable. Install FFmpeg on the backend, or paste a transcript instead.") from None
    except (subprocess.SubprocessError, OSError, ValueError, TypeError, AttributeError):
        raise AudioAnalysisError(422, "Could not decode this recording. Try a WAV export or another file.") from None
    pcm = decoded.stdout
    duration = len(pcm) / (SAMPLE_RATE * 2)
    if duration > MAX_DURATION_SECONDS:
        raise AudioAnalysisError(413, "Choose a recording no longer than two minutes.")
    if not pcm or len(pcm) % 2:
        raise AudioAnalysisError(422, "No usable audio was found in this recording.")
    samples = array.array("h", pcm)
    if sys.byteorder != "little":
        samples.byteswap()
    rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
    if rms < 32:
        raise AudioAnalysisError(422, "The recording is silent or too quiet. Try a clearer recording or paste a transcript.")
    return pcm, duration


def transcribe_audio(wav_path: Path, output_prefix: Path) -> tuple[str, str | None]:
    model = Path(os.environ.get("WHISPER_MODEL_PATH", str(DEFAULT_MODEL_PATH))).expanduser()
    if not model.is_absolute():
        model = BACKEND_DIR / model
    language = os.environ.get("WHISPER_LANGUAGE", "auto").strip().lower()
    try:
        timeout = float(os.environ.get("WHISPER_TIMEOUT_SECONDS", "120"))
        if not math.isfinite(timeout) or not 1 <= timeout <= 300:
            raise ValueError
    except ValueError:
        raise AudioAnalysisError(503, "WHISPER_TIMEOUT_SECONDS must be between 1 and 300 seconds.") from None
    if language not in {"auto", "en", "hi", "ta"}:
        raise AudioAnalysisError(503, "WHISPER_LANGUAGE must be auto, en, hi or ta.")
    if not model.is_file() or ".en" in model.name:
        raise AudioAnalysisError(503, "Local transcription needs a multilingual Whisper model. Configure WHISPER_MODEL_PATH on the backend, or paste a transcript instead.")
    if not TRANSCRIPTION_SLOT.acquire(blocking=False):
        raise AudioAnalysisError(503, "Another recording is being transcribed. Please try again shortly.")
    try:
        # No shell, translation flag, prompts from input, remote model downloads,
        # or stdout/stderr logging. JSON stays inside the private temp directory.
        subprocess.run([
            "whisper-cli", "-m", str(model), "-f", str(wav_path), "-l", language,
            "-t", "4", "-ng", "-oj", "-of", str(output_prefix),
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout, check=True)
        output = output_prefix.with_suffix(".json")
        if output.stat().st_size > 1024 * 1024:
            raise ValueError
        result = json.loads(output.read_text(encoding="utf-8"))
        segments = result["transcription"]
        if not isinstance(segments, list):
            raise ValueError
        texts = []
        for segment in segments:
            text = segment["text"]
            if not isinstance(text, str):
                raise ValueError
            text = text.strip()
            if not text or re.fullmatch(r"[\[(](?:blank_audio|silence|no speech|music|inaudible|applause)[\])]", text, re.IGNORECASE):
                continue
            texts.append(text)
        transcript = unicodedata.normalize("NFC", "\n".join(texts)).strip()
        detected_language = result.get("result", {}).get("language")
        if not isinstance(detected_language, str) or not re.fullmatch(r"[a-z]{2,3}", detected_language):
            detected_language = None
    except FileNotFoundError:
        raise AudioAnalysisError(503, "Local transcription is unavailable. Install whisper.cpp and its multilingual model, or paste a transcript instead.") from None
    except (subprocess.SubprocessError, OSError, ValueError, KeyError, TypeError, AttributeError):
        raise AudioAnalysisError(503, "Could not transcribe this recording. Try a shorter, clearer recording or paste a transcript instead.") from None
    finally:
        TRANSCRIPTION_SLOT.release()
    if not transcript:
        raise AudioAnalysisError(422, "No speech was recognized. Try a clearer recording or paste a transcript.")
    return transcript, detected_language


def analyze_audio(data: bytes, content_type: str | None) -> AudioAnalysisResponse:
    format_name = validate_upload(data, content_type)
    with tempfile.TemporaryDirectory(prefix="nazar-audio-") as directory:
        root = Path(directory)
        source = root / f"recording.{format_name}"
        source.write_bytes(data)
        pcm, duration = decode_audio(source, format_name)
        wav_path = root / "decoded.wav"
        with wave.open(str(wav_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(pcm)
        transcript, language = transcribe_audio(wav_path, root / "transcript")
    # Delete recording, decoded audio and JSON before invoking message analysis.
    if len(transcript) > MAX_TEXT_CHARS:
        raise AudioAnalysisError(413, "Transcript is too long. Upload a shorter recording.")
    analysis = analysis_service.analyze_text(transcript)
    if analysis.orchestration:
        analysis.orchestration.findings.append(AgentFinding(agent="voice_evidence", sources=["local_stt"], explanation="Transcript evidence only. Recognition errors are possible; speaker identity was not verified."))
    return AudioAnalysisResponse(
        transcript=transcript, analysis=analysis,
        audio=AudioMetadata(detected_language=language, duration_seconds=round(duration, 3), format=format_name),
    )
