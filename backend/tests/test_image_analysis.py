import io
import shutil
import subprocess
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont
from main import app
from schemas.analysis import MLAnalysis
from services.image_analysis import MAX_IMAGE_BYTES, analyze_image, extract_text, ImageAnalysisError, normalize_text
from services.text_analyzer import analyze_text


class ImageAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch("services.image_analysis.ocr_configuration", return_value={"language": "eng"}))
        self.client = TestClient(app)
        self.ocr = self.enterContext(patch("services.image_analysis.extract_text", return_value="Send me your OTP."))
        self.pipeline = self.enterContext(patch("services.image_analysis.analysis_service.analyze_text", return_value=analyze_text("Send me your OTP.")))

    def image(self, format="PNG"):
        out = io.BytesIO()
        Image.new("RGB", (200, 100), "white").save(out, format=format)
        return out.getvalue()

    def upload(self, data=None, mime="image/png"):
        return self.client.post("/api/analyze/image", files={"file": ("screenshot", self.image() if data is None else data, mime)})

    def test_valid_formats_reuse_existing_pipeline(self):
        for format, mime in (("PNG", "image/png"), ("JPEG", "image/jpeg"), ("WEBP", "image/webp")):
            with self.subTest(format=format):
                self.pipeline.reset_mock()
                self.ocr.return_value = " Send me\r\nyour OTP.  \n\f"
                response = self.upload(self.image(format), mime)
                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()
                self.assertEqual(result["extracted_text"], "Send me\nyour OTP.")
                self.pipeline.assert_called_once_with("Send me\nyour OTP.")
                self.assertEqual(result["analysis"]["score"], self.pipeline.return_value.score)
                self.assertEqual(result["ocr"]["image_format"], format)

    def test_unsupported_file(self):
        self.assertEqual(self.upload(b"not an image", "text/plain").status_code, 415)
        self.ocr.assert_not_called()
        self.pipeline.assert_not_called()

    def test_mismatched_mime(self):
        self.assertEqual(self.upload(self.image("JPEG"), "image/png").status_code, 415)
        self.ocr.assert_not_called()

    def test_invalid_and_truncated_image(self):
        for data in (b"", b"not an image", self.image()[:40]):
            self.assertEqual(self.upload(data).status_code, 422)
        self.pipeline.assert_not_called()

    def test_oversized_file(self):
        self.assertEqual(self.upload(b"x" * (MAX_IMAGE_BYTES + 1)).status_code, 413)
        self.assertEqual(self.upload(b"x" * (MAX_IMAGE_BYTES + 100_000)).status_code, 413)
        self.ocr.assert_not_called()

    def test_streamed_oversized_body(self):
        response = self.client.post("/api/analyze/image", content=iter([b"x" * (MAX_IMAGE_BYTES + 100_000)]), headers={"Content-Type": "multipart/form-data; boundary=x"})
        self.assertEqual(response.status_code, 413)

    def test_excessive_dimensions(self):
        with patch("services.image_analysis.MAX_IMAGE_PIXELS", 100):
            self.assertEqual(self.upload().status_code, 413)
        self.ocr.assert_not_called()

    def test_no_readable_text(self):
        self.ocr.return_value = "\n \f\t"
        response = self.upload()
        self.assertEqual(response.status_code, 422)
        self.assertIn("No readable text", response.json()["detail"])
        self.pipeline.assert_not_called()

    def test_ocr_failure(self):
        self.ocr.side_effect = ImageAnalysisError(503, "Text extraction unavailable.")
        self.assertEqual(self.upload().status_code, 503)
        self.pipeline.assert_not_called()

    def test_missing_upload(self):
        self.assertEqual(self.client.post("/api/analyze/image").status_code, 422)


class OCRTests(unittest.TestCase):
    def test_normalization_preserves_meaning(self):
        self.assertEqual(normalize_text(" Cafe\u0301:  pay $10!\r\nDo NOT send OTP.\f"), "Café: pay $10!\nDo NOT send OTP.")

    def test_engine_failures_are_safe(self):
        for failure in (FileNotFoundError("private path"), subprocess.TimeoutExpired("private command", 20), subprocess.CalledProcessError(1, "private command", stderr=b"secret")):
            with self.subTest(failure=type(failure)), patch("services.image_analysis.subprocess.run", side_effect=failure):
                with self.assertRaises(ImageAnalysisError) as caught:
                    extract_text(Image.new("RGB", (10, 10)))
                self.assertEqual(caught.exception.status_code, 503)
                self.assertNotIn("private", str(caught.exception))
                self.assertNotIn("secret", str(caught.exception))

    def test_engine_uses_bounded_local_pipes(self):
        with patch("services.image_analysis.subprocess.run", return_value=subprocess.CompletedProcess([], 0, b"Hello")) as run:
            self.assertEqual(extract_text(Image.new("RGB", (10, 10))), "Hello")
        self.assertEqual(run.call_args.args[0], ["tesseract", "stdin", "stdout", "-l", "eng", "--psm", "11"])
        self.assertEqual(run.call_args.kwargs["timeout"], 20)

    def test_v5_failure_still_returns_existing_analysis(self):
        out = io.BytesIO()
        Image.new("RGB", (100, 100)).save(out, format="PNG")
        with patch("services.image_analysis.ocr_configuration", return_value={"language": "eng"}), patch("services.image_analysis.extract_text", return_value="Send me your OTP."), patch("services.analysis_service.predict_scam_probability", return_value=MLAnalysis(available=False)), patch("services.llm.semantic_analyzer.configured_provider", side_effect=RuntimeError("secret")):
            result = analyze_image(out.getvalue(), "image/png")
        self.assertFalse(result.analysis.semantic.available)
        self.assertGreater(result.analysis.score, 0)
        self.assertNotIn("secret", result.model_dump_json())

    @unittest.skipUnless(shutil.which("tesseract"), "Local Tesseract is not installed")
    def test_real_ocr_screenshot(self):
        image = Image.new("RGB", (1200, 250), "white")
        ImageDraw.Draw(image).text((35, 80), "Send me your OTP immediately.", font=ImageFont.load_default(size=48), fill="black")
        text = extract_text(image)
        self.assertIn("OTP", text)
        self.assertIn("Send me", text)


if __name__ == "__main__":
    unittest.main()
