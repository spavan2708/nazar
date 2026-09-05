import unittest

from fastapi import HTTPException

from main import retrieve_campaign
from schemas.analysis import SignalCode, TextAnalysisResponse
from schemas.campaign import Interaction, InteractionRequest
from services import campaign_service


class CampaignTests(unittest.TestCase):
    def setUp(self):
        campaign_service._campaigns.clear()

    def test_create_campaign(self):
        campaign = campaign_service.create_campaign()

        self.assertTrue(campaign.campaign_id)
        self.assertEqual(campaign.campaign_score, 0)
        self.assertEqual(campaign.risk_level, "low")
        self.assertEqual(campaign.interactions, [])

    def test_harmless_interaction_keeps_risk_low(self):
        campaign = campaign_service.create_campaign()
        updated = self._add_text(campaign.campaign_id, "Let's meet for lunch tomorrow.")

        self.assertEqual(updated.campaign_score, 0)
        self.assertEqual(updated.risk_level, "low")
        self.assertEqual(updated.interactions[0].analysis.risk_level, "low")

    def test_kyc_urgency_raises_campaign_risk(self):
        campaign = campaign_service.create_campaign()
        updated = self._add_text(
            campaign.campaign_id, "Your KYC expires today. Verify immediately."
        )

        self.assertEqual(updated.campaign_score, 60)
        self.assertEqual(updated.risk_level, "medium")

    def test_remote_access_after_kyc_escalates_further(self):
        campaign = campaign_service.create_campaign()
        self._add_text(
            campaign.campaign_id, "Your KYC expires today. Verify immediately."
        )
        updated = self._add_text(
            campaign.campaign_id,
            "Install this screen-sharing app so I can help you.",
        )

        self.assertEqual(updated.campaign_score, 84)
        self.assertEqual(updated.risk_level, "high")

    def test_otp_after_remote_access_becomes_critical(self):
        campaign = campaign_service.create_campaign()
        self._add_text(
            campaign.campaign_id, "Your KYC expires today. Verify immediately."
        )
        self._add_text(
            campaign.campaign_id,
            "Install this screen-sharing app so I can help you.",
        )
        updated = self._add_text(
            campaign.campaign_id, "Tell me the OTP you received."
        )

        self.assertEqual(updated.campaign_score, 100)
        self.assertEqual(updated.risk_level, "critical")
        self.assertGreater(updated.interactions[-1].analysis.score, 0)

    def test_correlation_uses_structured_signals_not_raw_content(self):
        interaction = Interaction(
            interaction_id="test-interaction",
            type="text",
            content="KYC remote access OTP",
            analysis=TextAnalysisResponse(
                score=0,
                risk_level="low",
                signals=[],
                explanation="Test analysis with no detected signals.",
                recommended_action="No action.",
                signal_codes=set(),
            ),
        )

        self.assertEqual(campaign_service._calculate_campaign_score([interaction]), 0)

    def test_stored_analysis_retains_canonical_signals(self):
        campaign = campaign_service.create_campaign()
        updated = self._add_text(campaign.campaign_id, "Share your OTP")

        self.assertIn(
            SignalCode.OTP_REQUEST,
            updated.interactions[0].analysis.signal_codes,
        )

    def test_retrieve_existing_campaign(self):
        campaign = campaign_service.create_campaign()

        self.assertEqual(
            campaign_service.get_campaign(campaign.campaign_id).campaign_id,
            campaign.campaign_id,
        )

    def test_retrieve_invalid_campaign_returns_404(self):
        with self.assertRaises(HTTPException) as context:
            retrieve_campaign("missing-campaign")

        self.assertEqual(context.exception.status_code, 404)

    @staticmethod
    def _add_text(campaign_id: str, content: str):
        return campaign_service.add_interaction(
            campaign_id,
            InteractionRequest(type="text", content=content),
        )


if __name__ == "__main__":
    unittest.main()
