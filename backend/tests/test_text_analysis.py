import unittest

from pydantic import ValidationError

from main import app
from schemas.analysis import SignalCode, TextAnalysisRequest
from services.text_analyzer import analyze_text


class TextAnalysisTests(unittest.TestCase):
    def test_suspicious_kyc_message_is_high_risk(self):
        result = analyze_text(
            TextAnalysisRequest(
                text="Your KYC expires today. Click this link immediately."
            ).text
        )

        self.assertEqual(result.score, 90)
        self.assertEqual(result.risk_level, "high")
        self.assertEqual(len(result.signals), 3)

    def test_harmless_message_is_low_risk(self):
        result = analyze_text(
            TextAnalysisRequest(text="Let's meet for lunch tomorrow.").text
        )

        self.assertEqual(result.score, 0)
        self.assertEqual(result.risk_level, "low")
        self.assertEqual(result.signals, [])

    def test_blank_text_is_rejected(self):
        with self.assertRaises(ValidationError):
            TextAnalysisRequest(text="   ")

    def test_otp_request_has_individual_risk(self):
        result = analyze_text("Tell me the OTP you received.")

        self.assertGreater(result.score, 0)
        self.assertIn(SignalCode.OTP_REQUEST, result.signal_codes)

    def test_remote_access_has_individual_risk(self):
        result = analyze_text("Install this screen-sharing app so I can help you.")

        self.assertGreater(result.score, 0)
        self.assertIn(SignalCode.REMOTE_ACCESS, result.signal_codes)

    def test_credentials_have_individual_risk(self):
        result = analyze_text("Send your password and PIN")

        self.assertIn(SignalCode.CREDENTIAL_REQUEST, result.signal_codes)
        self.assertGreater(result.score, 0)

    def test_payment_and_urgency_are_detected(self):
        result = analyze_text("Transfer money now")

        self.assertIn(SignalCode.PAYMENT_REQUEST, result.signal_codes)
        self.assertIn(SignalCode.URGENCY, result.signal_codes)

    def test_analysis_route_is_registered(self):
        routes = {(route.path, tuple(route.methods or [])) for route in app.routes}
        self.assertTrue(
            any(
                path == "/api/analyze/text" and "POST" in methods
                for path, methods in routes
            )
        )


if __name__ == "__main__":
    unittest.main()
