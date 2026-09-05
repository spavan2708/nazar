"""Compositional code extraction: development regressions, never training rows."""
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app
from schemas.analysis import MLAnalysis
from schemas.semantic import SemanticAnalysis
from services.text_analyzer import analyze_text
from services.language_detection import identify_language
from tests.implicit_code_cases import ATTACKS, SAFE


class ImplicitCodeTests(unittest.TestCase):
    def test_paraphrases_and_supported_languages(self):
        for text in ATTACKS:
            with self.subTest(text=text):
                result = analyze_text(text)
                self.assertIn('OTP_REQUEST', result.signal_codes)
                self.assertFalse(result.context.is_safety_warning)
                self.assertNotEqual(result.risk_level, 'low')

    def test_matched_negatives(self):
        for text in SAFE:
            with self.subTest(text=text):
                self.assertEqual(analyze_text(text).signal_codes, set())

    def test_combinations_and_chat_noise(self):
        for obj in ('6 digit code', '6-digit number', 'six digit code', 'verification no', 'verifiction code'):
            for intent in ('bhejo', 'bhej do', 'send krdo', 'bta do', 'batao'):
                for pressure in ('jaldi', 'jldi', 'verification expire ho jayega'):
                    with self.subTest(obj=obj, intent=intent, pressure=pressure):
                        result = analyze_text(f'{obj} {intent} {pressure}')
                        self.assertTrue({'OTP_REQUEST', 'URGENCY'} <= result.signal_codes)
                        self.assertNotIn('OTP_REQUEST', analyze_text(f'{obj} kisi ko mat bhejna').signal_codes)

    def test_scope_and_non_authentication_objects(self):
        for text in ('Never share your OTP. Send me your password.',
                     'Never share your OTP, send me your password.',
                     'code kisi ko mat dena. mujhe lunch bhej do',
                     'send me your phone number', 'send me the six digit project code'):
            self.assertNotIn('OTP_REQUEST', analyze_text(text).signal_codes, text)
        self.assertIn('OTP_REQUEST', analyze_text('mera phone nahi chal raha, OTP bhej do').signal_codes)

    def test_exact_api_without_optional_detectors(self):
        with patch('services.analysis_service.predict_scam_probability', return_value=MLAnalysis(available=False)), patch('services.analysis_service.analyze_semantics', return_value=SemanticAnalysis(available=False)):
            client = TestClient(app)
            response = client.post('/api/analyze/text', json={'text': ATTACKS[0]})
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertGreater(data['score'], 0)
            self.assertNotEqual(data['risk_level'], 'low')
            self.assertTrue({'OTP_REQUEST', 'URGENCY'} <= set(data['intelligence']['deterministic']['signals']))
            self.assertTrue(data['explanation'])
            self.assertTrue(data['recommended_action'])
            self.assertEqual(data['original_text'], ATTACKS[0])
            safe = client.post('/api/analyze/text', json={'text': SAFE[4]}).json()
            self.assertNotIn('OTP_REQUEST', safe['intelligence']['deterministic']['signals'])
            self.assertEqual(safe['score'], 0)
        self.assertEqual(identify_language(ATTACKS[0]).detected_language, 'Hinglish')
