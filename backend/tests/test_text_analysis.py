import unittest

from pydantic import ValidationError

from main import app
from schemas.analysis import SignalCode, TextAnalysisRequest
from services.text_analyzer import analyze_text


class TextAnalysisTests(unittest.TestCase):
    def test_suspicious_kyc_message_is_critical_risk(self):
        result = analyze_text(
            TextAnalysisRequest(
                text="Your KYC expires today. Click this link immediately."
            ).text
        )

        self.assertEqual(result.score, 90)
        self.assertEqual(result.risk_level, "critical")
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

    def test_action_oriented_otp_request(self):
        result = analyze_text("Share your OTP with me immediately.")

        self.assertIn(SignalCode.OTP_REQUEST, result.signal_codes)
        self.assertIn(SignalCode.URGENCY, result.signal_codes)
        self.assertTrue(result.context.is_action_request)
        self.assertGreaterEqual(result.score, 70)

    def test_otp_safety_warning_is_low_risk(self):
        result = analyze_text("Never share your OTP with anyone.")

        self.assertNotIn(SignalCode.OTP_REQUEST, result.signal_codes)
        self.assertTrue(result.context.is_safety_warning)
        self.assertEqual(result.score, 0)
        self.assertEqual(result.risk_level, "low")

    def test_educational_otp_reference_is_low_risk(self):
        result = analyze_text("OTP means one-time password.")

        self.assertNotIn(SignalCode.OTP_REQUEST, result.signal_codes)
        self.assertFalse(result.context.is_action_request)
        self.assertEqual(result.score, 0)

    def test_action_oriented_remote_access_request(self):
        result = analyze_text("Install AnyDesk and share your screen.")

        self.assertIn(SignalCode.REMOTE_ACCESS, result.signal_codes)
        self.assertTrue(result.context.is_action_request)
        self.assertGreater(result.score, 0)

    def test_remote_access_safety_warning_is_low_risk(self):
        result = analyze_text("Do not install AnyDesk for unknown callers.")

        self.assertNotIn(SignalCode.REMOTE_ACCESS, result.signal_codes)
        self.assertTrue(result.context.is_safety_warning)
        self.assertEqual(result.score, 0)

    def test_informational_remote_access_reference_is_low_risk(self):
        result = analyze_text("AnyDesk is a remote access application.")

        self.assertNotIn(SignalCode.REMOTE_ACCESS, result.signal_codes)
        self.assertEqual(result.score, 0)

    def test_coercive_verification_pattern(self):
        result = analyze_text(
            "Your account will be blocked unless you verify immediately."
        )

        self.assertTrue(
            {
                SignalCode.ACCOUNT_THREAT,
                SignalCode.IDENTITY_VERIFICATION,
                SignalCode.URGENCY,
            }
            <= result.signal_codes
        )
        self.assertIn("coercive_verification", result.patterns)
        self.assertEqual(result.score, 100)

    def test_urgent_credential_request_pattern(self):
        result = analyze_text("Send your password now.")

        self.assertIn(SignalCode.CREDENTIAL_REQUEST, result.signal_codes)
        self.assertIn(SignalCode.URGENCY, result.signal_codes)
        self.assertIn("credential_theft", result.patterns)
        self.assertGreaterEqual(result.score, 70)

    def test_bank_credential_safety_advice_is_low_risk(self):
        result = analyze_text("Your bank will never ask you to share your PIN.")

        self.assertTrue(result.context.is_safety_warning)
        self.assertNotIn(SignalCode.CREDENTIAL_REQUEST, result.signal_codes)
        self.assertEqual(result.score, 0)

    def test_internal_metadata_is_not_serialized(self):
        result = analyze_text("Share your OTP")
        serialized = result.model_dump()

        self.assertNotIn("signal_codes", serialized)
        self.assertNotIn("context", serialized)
        self.assertNotIn("patterns", serialized)

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
