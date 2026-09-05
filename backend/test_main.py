import unittest

from pydantic import ValidationError

from main import TextAnalysisRequest, analyze_text, app


class TextAnalysisTests(unittest.TestCase):
    def test_suspicious_kyc_message_is_high_risk(self):
        result = analyze_text(
            TextAnalysisRequest(
                text="Your KYC expires today. Click this link immediately."
            )
        )

        self.assertEqual(result.score, 90)
        self.assertEqual(result.risk_level, "high")
        self.assertEqual(len(result.signals), 3)

    def test_harmless_message_is_low_risk(self):
        result = analyze_text(TextAnalysisRequest(text="Let's meet for lunch tomorrow."))

        self.assertEqual(result.score, 0)
        self.assertEqual(result.risk_level, "low")
        self.assertEqual(result.signals, [])

    def test_blank_text_is_rejected(self):
        with self.assertRaises(ValidationError):
            TextAnalysisRequest(text="   ")

    def test_analysis_route_is_registered(self):
        routes = {(route.path, tuple(route.methods or [])) for route in app.routes}
        self.assertTrue(
            any(path == "/api/analyze/text" and "POST" in methods for path, methods in routes)
        )


if __name__ == "__main__":
    unittest.main()
