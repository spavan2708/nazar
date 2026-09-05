import json
from pathlib import Path
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app
from schemas.analysis import MLAnalysis
from schemas.semantic import SemanticAnalysis
from schemas.signals import SignalCode
from services.text_analyzer import analyze_text

CASES = json.loads((Path(__file__).resolve().parents[1] / 'evaluation/v11_1_challenge.json').read_text())


class ImplicitRequestTests(unittest.TestCase):
    def test_challenge_sensitive_and_hard_negatives(self):
        for case in CASES:
            with self.subTest(text=case['text']):
                result = analyze_text(case['text'])
                sensitive = bool(result.signal_codes & {SignalCode.OTP_REQUEST, SignalCode.CREDENTIAL_REQUEST})
                self.assertEqual(sensitive, case['expected_sensitive'])
                if not case['expected_sensitive']:
                    self.assertEqual(result.signal_codes, set())
                    self.assertEqual(result.score, 0)

    def test_exact_regression_without_v4_v5(self):
        with patch('services.analysis_service.predict_scam_probability', return_value=MLAnalysis(available=False)), patch('services.analysis_service.analyze_semantics', return_value=SemanticAnalysis(available=False)):
            from services.analysis_service import analyze_text as pipeline
            result = pipeline(next(c['text'] for c in CASES if c['category'] == 'regression'))
            self.assertEqual(result.signal_codes, {SignalCode.OTP_REQUEST, SignalCode.URGENCY})
            self.assertEqual(result.score, 80)
            self.assertEqual(result.risk_level, 'high')

    def test_benign_qualifier_does_not_erase_explicit_secret(self):
        for text in ('I need your OTP for the test environment.', 'I need your password for the project code.'):
            self.assertTrue(analyze_text(text).signal_codes & {SignalCode.OTP_REQUEST, SignalCode.CREDENTIAL_REQUEST})

    def test_pressure_requires_sensitive_context(self):
        for pressure in ('quickly', 'before it expires', 'right now', 'immediately', 'only two minutes left', 'otherwise we have to wait two days'):
            with self.subTest(pressure=pressure):
                self.assertIn(SignalCode.URGENCY, analyze_text('I need your OTP ' + pressure).signal_codes)
                self.assertEqual(analyze_text(pressure).signal_codes, set())

    def test_independent_contextual_reinforcement(self):
        client = TestClient(app)
        with patch('services.analysis_service.predict_scam_probability', return_value=MLAnalysis(available=False)) as ml, patch('services.analysis_service.analyze_semantics', return_value=SemanticAnalysis(available=False)) as llm:
            cid = client.post('/api/campaigns').json()['campaign_id']
            route = f'/api/campaigns/{cid}/evidence/text'
            first = client.post(route, json={'text':'send me the otp'}).json()
            followup = 'we need it really quick before it expires'
            response = client.post(route, json={'text':followup})
            self.assertEqual(response.status_code, 200, response.text)
            campaign = response.json()
            item = campaign['interactions'][-1]
            self.assertEqual(item['analysis']['score'], 0)
            self.assertEqual(item['canonical_signal_codes'], [])
            self.assertEqual(item['stages'], [])
            self.assertEqual(item['new_stages'], [])
            self.assertEqual(campaign['campaign_score'], first['campaign_score'])
            reinforcement = item['contextual_reinforcements'][0]
            self.assertEqual(reinforcement['stage'], 'AUTHENTICATION_TAKEOVER')
            self.assertEqual(reinforcement['source_evidence_id'], first['interactions'][0]['interaction_id'])
            self.assertEqual(reinforcement['source_evidence_order'], 1)
            self.assertEqual([call.args[0] for call in llm.call_args_list], ['send me the otp', followup])
            self.assertEqual(ml.call_count, 2)
            self.assertEqual(client.get(f'/api/campaigns/{cid}').json(), campaign)

    def test_no_reinforcement_without_adjacent_sensitive_evidence_or_for_warning(self):
        client = TestClient(app)
        with patch('services.analysis_service.predict_scam_probability', return_value=MLAnalysis(available=False)), patch('services.analysis_service.analyze_semantics', return_value=SemanticAnalysis(available=False)):
            for messages in (
                ['we need it really quick before it expires'],
                ['send me the otp', 'Hello', 'we need it really quick before it expires'],
                ['send me the otp', 'Never share your OTP even if they need it quickly.'],
                ['send me the otp', 'I need the project code quickly'],
            ):
                cid = client.post('/api/campaigns').json()['campaign_id']
                for text in messages:
                    response = client.post(f'/api/campaigns/{cid}/evidence/text', json={'text':text})
                self.assertEqual(response.json()['interactions'][-1]['contextual_reinforcements'], [])
