import io
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from main import app
from schemas.analysis import MLAnalysis, TextAnalysisResponse
from schemas.semantic import SemanticAnalysis
from services.risk_fusion import fuse_risk
from services.risk_levels import risk_level_for_score
from services.text_analyzer import risk_guidance

BOUNDARIES = (
    (0, "low"), (29, "low"), (30, "medium"), (34, "medium"),
    (35, "medium"), (64, "medium"), (65, "high"), (69, "high"),
    (70, "high"), (84, "high"), (85, "critical"), (86, "critical"),
    (100, "critical"),
)


class RiskLevelTests(unittest.TestCase):
    def test_boundaries_and_fusion_preserve_raw_scores(self):
        for score, level in BOUNDARIES:
            with self.subTest(score=score):
                self.assertEqual(risk_level_for_score(score), level)
                self.assertEqual(risk_guidance(score)[0], level)
                result = fuse_risk(
                    TextAnalysisResponse(score=score, risk_level="low", signals=[],
                        explanation="Test", recommended_action="Test"),
                    MLAnalysis(available=False), SemanticAnalysis(available=False),
                )
                self.assertEqual(result.score, score)
                self.assertEqual(result.risk_level, level)

    def test_existing_recommended_actions_are_unchanged(self):
        for score in range(101):
            expected = (
                "Do not click or respond. Verify the request through the official organization."
                if score >= 70 else
                "Pause and verify the sender through a trusted channel before acting."
                if score >= 35 else
                "No common scam signs were detected, but stay cautious with unexpected requests."
            )
            self.assertEqual(risk_guidance(score)[1], expected)

    def test_all_api_paths_use_shared_boundary_labels(self):
        client = TestClient(app)
        image = io.BytesIO()
        Image.new("RGB", (20, 20)).save(image, format="PNG")
        for score, level in BOUNDARIES:
            with self.subTest(score=score), patch(
                "services.analysis_service.analyze_text_deterministically",
                return_value=TextAnalysisResponse(score=score, risk_level="low",
                    signals=[], explanation="Test", recommended_action="Test"),
            ), patch("services.analysis_service.predict_scam_probability", return_value=MLAnalysis(available=False)), patch(
                "services.analysis_service.analyze_semantics", return_value=SemanticAnalysis(available=False)
            ), patch("services.image_analysis.ocr_configuration", return_value={"language": "eng"}), patch("services.image_analysis.extract_text", return_value="Test message"):
                text = client.post("/api/analyze/text", json={"text": "Test message"})
                screenshot = client.post("/api/analyze/image", files={"file": ("test.png", image.getvalue(), "image/png")})
                campaign = client.post("/api/campaigns")
                self.assertEqual(campaign.status_code, 200)
                cid = campaign.json()["campaign_id"]
                sequence = client.post(f"/api/campaigns/{cid}/interactions", json={"type": "text", "content": "Test message"})
                for response in (text, screenshot, sequence):
                    self.assertEqual(response.status_code, 200, response.text)
                for result in (text.json(), screenshot.json()["analysis"], sequence.json()["interactions"][0]["analysis"]):
                    self.assertEqual(result["score"], score)
                    self.assertEqual(result["risk_level"], level)
                # One signal-free interaction has no campaign bonuses.
                self.assertEqual(sequence.json()["campaign_score"], score)
                self.assertEqual(sequence.json()["risk_level"], level)
                self.assertEqual(client.get(f"/api/campaigns/{cid}").json()["risk_level"], level)


if __name__ == "__main__":
    unittest.main()
