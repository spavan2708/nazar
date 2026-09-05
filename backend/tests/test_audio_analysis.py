import io
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import wave

from fastapi.testclient import TestClient

from main import app
from schemas.analysis import MLAnalysis
from schemas.semantic import SemanticAnalysis
from services import audio_analysis as audio
from services.text_analyzer import analyze_text


def wav_bytes(seconds=0.2, silent=False):
    output = io.BytesIO()
    samples = b"".join(struct.pack("<h", 0 if silent else int(3000 * math.sin(2 * math.pi * 440 * i / 16000))) for i in range(int(seconds * 16000)))
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(samples)
    return output.getvalue()


class AudioAPITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.decode = self.enterContext(patch("services.audio_analysis.decode_audio", return_value=(b"\x01\x01" * 3200, 0.2)))
        self.transcribe = self.enterContext(patch("services.audio_analysis.transcribe_audio", return_value=("Send me your OTP.", "en")))
        self.pipeline = self.enterContext(patch("services.audio_analysis.analysis_service.analyze_text", return_value=analyze_text("Send me your OTP.")))

    def upload(self, data=None, mime="audio/wav"):
        return self.client.post("/api/analyze/audio", files={"file": ("untrusted-name.wav", wav_bytes() if data is None else data, mime)})

    def test_valid_audio_reuses_pipeline_and_cleans_up(self):
        paths = []
        def transcribe(wav, output):
            self.assertTrue(wav.exists())
            paths.append(wav.parent)
            return "Send me your OTP.", "en"
        self.transcribe.side_effect = transcribe
        response = self.upload()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["transcript"], "Send me your OTP.")
        self.assertEqual(response.json()["audio"], {"engine": "whisper.cpp", "detected_language": "en", "duration_seconds": 0.2, "format": "wav"})
        self.pipeline.assert_called_once_with("Send me your OTP.")
        self.assertFalse(paths[0].exists())

    def test_unsupported_and_malformed(self):
        self.assertEqual(self.upload(b"bad", "audio/ogg").status_code, 415)
        self.assertEqual(self.upload(b"bad").status_code, 422)
        self.assertEqual(self.upload(b"").status_code, 422)
        self.assertEqual(self.upload(wav_bytes(), "audio/mpeg").status_code, 422)
        self.decode.assert_not_called()
        self.pipeline.assert_not_called()

    def test_oversized_upload_and_stream(self):
        self.assertEqual(self.upload(b"x" * (audio.MAX_AUDIO_BYTES + 1)).status_code, 413)
        response = self.client.post("/api/analyze/audio", content=iter([b"x" * (audio.MAX_AUDIO_BYTES + 100_000)]), headers={"Content-Type": "multipart/form-data; boundary=x"})
        self.assertEqual(response.status_code, 413)
        self.decode.assert_not_called()

    def test_duration_silence_and_decode_failures(self):
        for status, message in ((413, "Too long"), (422, "Silent"), (422, "Malformed")):
            self.decode.side_effect = audio.AudioAnalysisError(status, message)
            self.assertEqual(self.upload().status_code, status)
        self.transcribe.assert_not_called()
        self.pipeline.assert_not_called()

    def test_transcription_failure_cleans_up(self):
        paths = []
        def fail(wav, output):
            paths.append(wav.parent)
            raise audio.AudioAnalysisError(503, "Transcription unavailable")
        self.transcribe.side_effect = fail
        self.assertEqual(self.upload().status_code, 503)
        self.assertFalse(paths[0].exists())
        self.pipeline.assert_not_called()

    def test_multilingual_transcript_is_not_translated(self):
        for language, transcript in (("hi", "अपना ओटीपी साझा करें"), ("ta", "உங்கள் OTP பகிரவும்")):
            self.pipeline.reset_mock()
            self.transcribe.return_value = transcript, language
            response = self.upload()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["transcript"], transcript)
            self.assertEqual(response.json()["audio"]["detected_language"], language)
            self.pipeline.assert_called_once_with(transcript)

    def test_missing_file(self):
        self.assertEqual(self.client.post("/api/analyze/audio").status_code, 422)


class DecoderTests(unittest.TestCase):
    def test_probe_rejects_duration_before_decode(self):
        probe = subprocess.CompletedProcess([], 0, json.dumps({"streams": [{"codec_type": "audio"}], "format": {"duration": "121"}}).encode())
        with patch("services.audio_analysis.subprocess.run", return_value=probe) as run, self.assertRaises(audio.AudioAnalysisError) as caught:
            audio.decode_audio(Path("/tmp/generated.wav"), "wav")
        self.assertEqual(caught.exception.status_code, 413)
        self.assertEqual(run.call_count, 1)

    def test_actual_decoded_duration_is_bounded(self):
        probe = subprocess.CompletedProcess([], 0, b'{"streams":[{"codec_type":"audio"}]}')
        decoded = subprocess.CompletedProcess([], 0, b"\x00\x10" * 32000)
        with patch("services.audio_analysis.MAX_DURATION_SECONDS", 1), patch("services.audio_analysis.subprocess.run", side_effect=[probe, decoded]), self.assertRaises(audio.AudioAnalysisError) as caught:
            audio.decode_audio(Path("/tmp/generated.wav"), "wav")
        self.assertEqual(caught.exception.status_code, 413)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "Install FFmpeg for real decoder checks")
    def test_real_supported_decoders_and_silence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.wav"
            source.write_bytes(wav_bytes())
            for suffix, codec in (("wav", "pcm_s16le"), ("mp3", "libmp3lame"), ("m4a", "aac"), ("webm", "libopus")):
                target = root / f"converted.{suffix}"
                subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(source), "-c:a", codec, str(target)], check=True, timeout=15, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                with self.subTest(format=suffix):
                    audio.validate_upload(target.read_bytes(), {"wav": "audio/wav", "mp3": "audio/mpeg", "m4a": "audio/mp4", "webm": "audio/webm"}[suffix])
                    pcm, duration = audio.decode_audio(target, suffix)
                    self.assertTrue(pcm)
                    self.assertGreater(duration, 0)
                    self.assertLess(duration, 1)
            source.write_bytes(wav_bytes(silent=True))
            with self.assertRaises(audio.AudioAnalysisError) as caught:
                audio.decode_audio(source, "wav")
            self.assertEqual(caught.exception.status_code, 422)
            source.write_bytes(b"RIFF\x00\x00\x00\x00WAVEbad-data")
            with self.assertRaises(audio.AudioAnalysisError):
                audio.decode_audio(source, "wav")


class TranscriptionTests(unittest.TestCase):
    def test_original_language_json_and_no_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / "model.bin"
            model.touch()
            output = root / "output"
            payload = "உங்கள் OTP பகிரவும் https://example.com $(not-a-command)"
            def run(command, **kwargs):
                self.assertNotIn("-tr", command)
                self.assertNotIn(payload, command)
                self.assertFalse(kwargs.get("shell", False))
                output.with_suffix(".json").write_text(json.dumps({"result": {"language": "ta"}, "transcription": [{"text": payload}]}))
            with patch.dict(os.environ, {"WHISPER_MODEL_PATH": str(model), "WHISPER_LANGUAGE": "auto", "WHISPER_TIMEOUT_SECONDS": "120"}), patch("services.audio_analysis.subprocess.run", side_effect=run), self.assertNoLogs(level="DEBUG"):
                self.assertEqual(audio.transcribe_audio(root / "audio.wav", output), (payload, "ta"))

    def test_no_speech_json_and_failure_are_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / "model.bin"
            model.touch()
            output = root / "output"
            output.with_suffix(".json").write_text(json.dumps({"transcription": [{"text": "[BLANK_AUDIO]"}]}))
            with patch.dict(os.environ, {"WHISPER_MODEL_PATH": str(model)}), patch("services.audio_analysis.subprocess.run"), self.assertRaises(audio.AudioAnalysisError) as caught:
                audio.transcribe_audio(root / "audio.wav", output)
            self.assertEqual(caught.exception.status_code, 422)
            for failure in (FileNotFoundError("secret"), subprocess.TimeoutExpired("secret", 120), subprocess.CalledProcessError(1, "secret")):
                with patch.dict(os.environ, {"WHISPER_MODEL_PATH": str(model)}), patch("services.audio_analysis.subprocess.run", side_effect=failure), self.assertRaises(audio.AudioAnalysisError) as caught:
                    audio.transcribe_audio(root / "audio.wav", output)
                self.assertEqual(caught.exception.status_code, 503)
                self.assertNotIn("secret", str(caught.exception))

    def test_missing_model_and_invalid_configuration(self):
        for settings in ({"WHISPER_MODEL_PATH": "/nonexistent/model.bin"}, {"WHISPER_TIMEOUT_SECONDS": "nan"}, {"WHISPER_LANGUAGE": "auto;echo secret"}):
            with patch.dict(os.environ, settings), self.assertRaises(audio.AudioAnalysisError):
                audio.transcribe_audio(Path("/tmp/audio.wav"), Path("/tmp/output"))

    def test_busy_slot_returns_safe_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "model.bin"
            model.touch()
            audio.TRANSCRIPTION_SLOT.acquire()
            try:
                with patch.dict(os.environ, {"WHISPER_MODEL_PATH": str(model)}), self.assertRaises(audio.AudioAnalysisError) as caught:
                    audio.transcribe_audio(Path("/tmp/audio.wav"), Path("/tmp/output"))
                self.assertEqual(caught.exception.status_code, 503)
            finally:
                audio.TRANSCRIPTION_SLOT.release()


class AudioIntegrationTests(unittest.TestCase):
    def test_existing_analysis_and_url_intelligence(self):
        with patch("services.audio_analysis.decode_audio", return_value=(b"\x01\x01" * 3200, 0.2)), patch("services.audio_analysis.transcribe_audio", return_value=("Visit http://192.0.2.1:8080/", "en")), patch("services.analysis_service.predict_scam_probability", return_value=MLAnalysis(available=False)), patch("services.analysis_service.analyze_semantics", return_value=SemanticAnalysis(available=False)):
            response = TestClient(app).post("/api/analyze/audio", files={"file": ("audio.wav", wav_bytes(), "audio/wav")})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["analysis"]["urls"][0]["hostname"], "192.0.2.1")
        self.assertEqual(response.json()["analysis"]["original_text"], response.json()["transcript"])

    @unittest.skipUnless(os.environ.get("NAZAR_REAL_AUDIO_TEST") == "1", "Set NAZAR_REAL_AUDIO_TEST=1 for the optional local Whisper integration test")
    def test_real_local_english_transcription(self):
        if not all(shutil.which(tool) for tool in ("say", "ffmpeg", "ffprobe", "whisper-cli")) or not audio.DEFAULT_MODEL_PATH.exists():
            self.skipTest("Install macOS speech, FFmpeg, whisper.cpp and the base model")
        with tempfile.TemporaryDirectory() as directory:
            aiff = Path(directory) / "speech.aiff"
            subprocess.run(["say", "-v", "Samantha", "-o", str(aiff), "Please send me your password immediately. Do not tell anyone about this call."], check=True, timeout=30)
            wav = Path(directory) / "speech.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-i", str(aiff), "-ar", "16000", "-ac", "1", str(wav)], check=True, timeout=15)
            with patch.dict(os.environ, {"WHISPER_LANGUAGE": "en", "WHISPER_MODEL_PATH": str(audio.DEFAULT_MODEL_PATH)}), patch("services.analysis_service.predict_scam_probability", return_value=MLAnalysis(available=False)), patch("services.analysis_service.analyze_semantics", return_value=SemanticAnalysis(available=False)):
                result = audio.analyze_audio(wav.read_bytes(), "audio/wav")
            self.assertIn("password", result.transcript.lower())
            self.assertEqual(result.audio.detected_language, "en")
            self.assertGreater(result.analysis.score, 0)


if __name__ == "__main__":
    unittest.main()
