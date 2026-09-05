import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from main import app
from schemas.analysis import MLAnalysis
from schemas.semantic import SemanticAnalysis
from schemas.signals import SignalCode
from schemas.stages import ScamStage
from services.text_analyzer import analyze_text
from services.investigation_stages import derive_stages, apply_stages, SIGNAL_STAGES
from services import campaign_service
from schemas.campaign import Campaign, Interaction

DEMO = [
    'Your bank KYC expires today. Verify your account immediately.',
    'http://192.0.2.1:8080/login/verify/account',
    'Install the remote support application so our agent can connect.',
    'Now send me the OTP that just arrived on your phone.',
]
SAFE = [
    'Never install remote access software for an unknown caller.',
    'Do not allow strangers to control your device remotely.',
    'Bank staff will never ask you to install AnyDesk.',
]


class RemoteAccessTests(unittest.TestCase):
    def test_compositional_requests_without_ml_or_llm(self):
        for text in [DEMO[2],
            'Download the support tool and let the technician connect.',
            'Open AnyDesk and allow remote access.',
            'Share your screen with our support executive.',
            'Install the app so I can control the device remotely.',
            'Allow the technician to connect to your computer.',
            'Download our remote-control program.',
            'Allow screen sharing.',
            'Remote support app install karo, agent ko connect karne do.',
            'Remote support app install pannunga.',
        ]:
            with self.subTest(text=text):
                result = analyze_text(text)
                self.assertIn(SignalCode.REMOTE_ACCESS, result.signal_codes)
                self.assertEqual(result.score, 45)
                self.assertTrue(result.context.is_action_request)

    def test_safety_and_benign_mentions(self):
        for text in SAFE + [
            'Remote support applications are used by technicians.',
            'Download the support manual and read it.',
            'Let the technician connect the printer.',
            'Install the weather app to see the forecast.',
            'Install the support tool. The train will connect two cities.',
            'Remote support app install mat karo.',
            'Remote support app install panna vendam.',
        ]:
            with self.subTest(text=text):
                result = analyze_text(text)
                self.assertNotIn(SignalCode.REMOTE_ACCESS, result.signal_codes)
                self.assertEqual(derive_stages(result), [])

    def test_warning_does_not_hide_separate_instruction(self):
        result = analyze_text('Never install remote software from strangers. Now send me your OTP.')
        self.assertIn(SignalCode.OTP_REQUEST, result.signal_codes)
        self.assertIn(ScamStage.AUTHENTICATION_TAKEOVER, derive_stages(result))


class StageTests(unittest.TestCase):
    def test_all_signal_mappings_and_no_mutation(self):
        self.assertEqual(set(SIGNAL_STAGES), set(SignalCode))
        expected = {
            SignalCode.BANK_IMPERSONATION: ScamStage.IMPERSONATION,
            SignalCode.GOVERNMENT_IMPERSONATION: ScamStage.IMPERSONATION,
            SignalCode.IDENTITY_VERIFICATION: ScamStage.VERIFICATION_PRETEXT,
            SignalCode.LINK_REQUEST: ScamStage.LINK_REDIRECTION,
            SignalCode.REMOTE_ACCESS: ScamStage.REMOTE_ACCESS,
            SignalCode.CREDENTIAL_REQUEST: ScamStage.CREDENTIAL_HARVESTING,
            SignalCode.OTP_REQUEST: ScamStage.AUTHENTICATION_TAKEOVER,
            SignalCode.PAYMENT_REQUEST: ScamStage.PAYMENT_EXTRACTION,
            SignalCode.URGENCY: ScamStage.URGENCY_OR_PRESSURE,
            SignalCode.ACCOUNT_THREAT: ScamStage.URGENCY_OR_PRESSURE,
            SignalCode.INVESTMENT_PROMISE: ScamStage.INVESTMENT_LURE,
        }
        for code, stage in expected.items():
            result = analyze_text('Hello').model_copy(update={'signal_codes': {code}})
            before = result.model_copy(deep=True)
            self.assertEqual(derive_stages(result), [stage])
            self.assertEqual(result, before)

    def test_safety_metadata_and_no_score_based_stages(self):
        for text in SAFE:
            result = analyze_text(text)
            result.signal_codes = {SignalCode.REMOTE_ACCESS}
            self.assertEqual(derive_stages(result), [])
        result = analyze_text('Hello').model_copy(update={'score': 100})
        self.assertEqual(derive_stages(result), [])

    def test_repeated_stage_and_benign_item(self):
        campaign = Campaign(campaign_id='test', campaign_score=45, risk_level='medium', interactions=[])
        for order, text in enumerate([DEMO[2], DEMO[2], 'Hello'], 1):
            item = Interaction(interaction_id=str(order), type='text', order=order, content=text, analysis=analyze_text(text))
            before = campaign_service._calculate_campaign_score([*campaign.interactions, item])
            apply_stages(campaign, item)
            self.assertEqual(campaign_service._calculate_campaign_score([*campaign.interactions, item]), before)
            campaign.interactions.append(item)
            self.assertEqual(item.current_stage_after, ScamStage.REMOTE_ACCESS)
            if order > 1: self.assertEqual(item.new_stages, [])
        self.assertEqual(len(campaign.stage_progression), 1)
        self.assertEqual(campaign.campaign_score, 45)

    def test_local_demo_capped_risk_progresses_and_retries_do_not_infer(self):
        client = TestClient(app)
        with patch('services.analysis_service.predict_scam_probability', return_value=MLAnalysis(available=False)), patch('services.analysis_service.analyze_semantics', return_value=SemanticAnalysis(available=False)) as llm:
            cid = client.post('/api/campaigns').json()['campaign_id']
            base = f'/api/campaigns/{cid}'
            results = []
            for index, text in enumerate(DEMO):
                # Legacy text route remains compatible and gets additive stages.
                if index == 0:
                    response = client.post(base + '/interactions', json={'type': 'text', 'content': text})
                else:
                    kind = 'url' if index == 1 else 'text'
                    key = str(uuid4())
                    response = client.post(base + '/evidence/' + kind, json={kind: text}, headers={'Idempotency-Key': key})
                    retry = client.post(base + '/evidence/' + kind, json={kind: text}, headers={'Idempotency-Key': key})
                    self.assertEqual(response.json(), retry.json())
                self.assertEqual(response.status_code, 200, response.text)
                results.append(response.json())
            self.assertEqual(llm.call_count, 4)
            final = results[-1]
            items = final['interactions']
            self.assertEqual(items[2]['analysis']['score'], 45)
            self.assertIn('REMOTE_ACCESS', items[2]['canonical_signal_codes'])
            self.assertEqual(items[2]['new_stages'], ['REMOTE_ACCESS'])
            self.assertEqual(items[3]['new_stages'], ['AUTHENTICATION_TAKEOVER'])
            self.assertEqual([r['campaign_score'] for r in results], [85, 100, 100, 100])
            self.assertEqual([item['risk_delta'] for item in items][2:], [0, 0])
            self.assertEqual([step['current_stage'] for step in final['stage_progression']], ['IMPERSONATION', 'LINK_REDIRECTION', 'REMOTE_ACCESS', 'AUTHENTICATION_TAKEOVER'])
            self.assertEqual(final['current_stage'], 'AUTHENTICATION_TAKEOVER')
            self.assertEqual(len(final['stages']), len(set(final['stages'])))
            self.assertEqual(client.get(base).json(), final)
            self.assertIn('appears to progress', final['stage_explanation'])
            stored = campaign_service.get_campaign(cid)
            self.assertEqual(stored.campaign_score, campaign_service._calculate_campaign_score(stored.interactions))

    def test_safe_campaign_adds_no_attack_stages(self):
        client = TestClient(app)
        with patch('services.analysis_service.predict_scam_probability', return_value=MLAnalysis(available=False)), patch('services.analysis_service.analyze_semantics', return_value=SemanticAnalysis(available=False)):
            cid = client.post('/api/campaigns').json()['campaign_id']
            for text in SAFE:
                response = client.post(f'/api/campaigns/{cid}/evidence/text', json={'text': text})
                self.assertEqual(response.status_code, 200)
                result = response.json()
                self.assertEqual(result['stages'], [])
                self.assertEqual(result['stage_progression'], [])
                self.assertIsNone(result['current_stage'])
                self.assertEqual(result['campaign_score'], 0)
