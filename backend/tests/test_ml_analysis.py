import unittest
from unittest.mock import patch

from ml.classifier import predict_scam_probability
from schemas.analysis import MLAnalysis
from services.analysis_service import analyze_text
from services.risk_fusion import fuse_risk
from services.text_analyzer import analyze_text as analyze_text_deterministically


class MLAnalysisTests(unittest.TestCase):
    def test_probability_is_bounded(self):
        result = predict_scam_probability("Please send the code from your phone.")

        self.assertTrue(result.available)
        self.assertGreaterEqual(result.scam_probability, 0.0)
        self.assertLessEqual(result.scam_probability, 1.0)

    def test_unseen_suspicious_paraphrase_scores_above_harmless_text(self):
        suspicious = predict_scam_probability(
            "Pass me the number that just appeared on your handset."
        )
        harmless = predict_scam_probability("Would you like tea after the meeting?")

        self.assertTrue(suspicious.available)
        self.assertTrue(harmless.available)
        self.assertGreater(suspicious.scam_probability, harmless.scam_probability)

    def test_safety_warning_is_comparatively_low(self):
        warning = predict_scam_probability(
            "Never reveal verification numbers to callers."
        )
        suspicious = predict_scam_probability(
            "Pass me the verification number that appeared on your phone."
        )

        self.assertLess(warning.scam_probability, suspicious.scam_probability)

    @patch("services.analysis_service.analyze_semantics")
    @patch("services.analysis_service.predict_scam_probability")
    def test_deterministic_analysis_survives_unavailable_ml(
        self, predict, semantic
    ):
        predict.return_value = MLAnalysis(available=False, model_version="v1")
        semantic.return_value = None

        result = analyze_text("Your KYC expires today. Click this link immediately.")

        self.assertEqual(result.score, 90)
        self.assertEqual(result.risk_level, "critical")
        self.assertFalse(result.ml.available)

    def test_low_ml_probability_cannot_downgrade_critical_pattern(self):
        deterministic = analyze_text_deterministically(
            "Install AnyDesk and send me your OTP immediately."
        )
        result = fuse_risk(
            deterministic,
            MLAnalysis(
                available=True,
                scam_probability=0.01,
                model_version="v1",
            ),
        )

        self.assertEqual(result.score, 100)
        self.assertEqual(result.risk_level, "critical")

    def test_high_ml_confidence_can_raise_weak_deterministic_result(self):
        deterministic = analyze_text_deterministically(
            "Pass me the number that just appeared on your handset."
        )
        result = fuse_risk(
            deterministic,
            MLAnalysis(
                available=True,
                scam_probability=0.90,
                model_version="v1",
            ),
        )

        self.assertEqual(deterministic.score, 0)
        self.assertEqual(result.score, 50)
        self.assertEqual(result.risk_level, "medium")


if __name__ == "__main__":
    unittest.main()
