import io
import unittest
from uuid import uuid4
from unittest.mock import patch
from fastapi.testclient import TestClient
from PIL import Image
from main import app
from schemas.analysis import MLAnalysis
from schemas.semantic import SemanticAnalysis, SemanticSignal
from schemas.signals import SignalCode
from services import campaign_service
from services.image_analysis import ImageAnalysisError, MAX_IMAGE_BYTES
from services.audio_analysis import AudioAnalysisError, MAX_AUDIO_BYTES
from test_audio_analysis import wav_bytes

KYC = 'Your bank KYC expires today. Verify your account immediately.'
LINK = 'http://192.0.2.1:8080/login/verify/account'
VOICE = 'Install the remote support app so our agent can connect.'
OTP = 'Now send me the OTP that just arrived on your phone.'

class InvestigationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.new_campaign()
        self.enterContext(patch('services.analysis_service.predict_scam_probability', return_value=MLAnalysis(available=False)))
        def semantic(text):
            if text == VOICE:
                return SemanticAnalysis(available=True, risk_score=.95, explanation='Remote access request.', signals=[SemanticSignal(code=SignalCode.REMOTE_ACCESS, confidence=.99)], provider='private-provider', model_version='/private/model')
            return SemanticAnalysis(available=False)
        self.llm = self.enterContext(patch('services.analysis_service.analyze_semantics', side_effect=semantic))
        self.ocr = self.enterContext(patch('services.image_analysis.extract_text', return_value=KYC))
        self.enterContext(patch('services.image_analysis.ocr_configuration', return_value={'language': 'eng'}))
        self.enterContext(patch('services.audio_analysis.decode_audio', return_value=(b'\x01\x01' * 3200, .2)))
        self.paths = []
        def transcribe(wav, output):
            self.paths.append(wav.parent)
            return VOICE, 'en'
        self.stt = self.enterContext(patch('services.audio_analysis.transcribe_audio', side_effect=transcribe))

    def new_campaign(self):
        self.cid = self.client.post('/api/campaigns').json()['campaign_id']
        self.base = f'/api/campaigns/{self.cid}'

    def image(self):
        out = io.BytesIO()
        Image.new('RGB', (200, 100), 'white').save(out, format='PNG')
        return out.getvalue()

    def add(self, kind, value, key=None):
        headers = {'Idempotency-Key': key} if key else {}
        if kind in ('image', 'audio'):
            return self.client.post(f'{self.base}/evidence/{kind}', headers=headers, files={'file': ('private-filename', value, 'image/png' if kind == 'image' else 'audio/wav')})
        return self.client.post(f'{self.base}/evidence/{kind}', headers=headers, json={kind: value})

    def test_mixed_sequence_preserves_signals_history_and_calls_once(self):
        for first in ('text', 'image'):
            with self.subTest(first=first):
                self.new_campaign()
                self.llm.reset_mock(); self.ocr.reset_mock(); self.stt.reset_mock()
                results = []
                for kind, value in ((first, KYC if first == 'text' else self.image()), ('url', LINK), ('audio', wav_bytes()), ('text', OTP)):
                    response = self.add(kind, value)
                    self.assertEqual(response.status_code, 200, response.text)
                    results.append(response.json())
                final = results[-1]
                self.assertEqual(final['evidence_count'], 4)
                items = final['interactions']
                self.assertEqual([i['type'] for i in items], [first if first == 'text' else 'screenshot', 'url', 'audio', 'text'])
                self.assertEqual([i['order'] for i in items], [1, 2, 3, 4])
                self.assertEqual([i['campaign_score_after'] for i in items], [r['campaign_score'] for r in results])
                previous = 0
                for item in items:
                    self.assertEqual(item['risk_delta'], item['campaign_score_after'] - previous)
                    previous = item['campaign_score_after']
                for code in ('IDENTITY_VERIFICATION', 'LINK_REQUEST', 'REMOTE_ACCESS', 'OTP_REQUEST'):
                    self.assertIn(code, final['canonical_signal_codes'])
                self.assertGreater(final['campaign_score'], results[0]['campaign_score'])
                self.assertEqual(final['campaign_score'], campaign_service._calculate_campaign_score(campaign_service.get_campaign(self.cid).interactions))
                self.assertEqual(self.llm.call_count, 4)
                self.assertEqual(self.ocr.call_count, int(first == 'image'))
                self.stt.assert_called_once()
                self.assertEqual(self.client.get(self.base).json(), final)
                self.assertTrue(all(not path.exists() for path in self.paths))
                serialized = campaign_service.get_campaign(self.cid).model_dump_json()
                for private in ('private-filename', 'private-provider', '/private/model'):
                    self.assertNotIn(private, serialized)
                self.assertEqual(items[2]['transcript'], VOICE)
                if first == 'image': self.assertEqual(items[0]['extracted_text'], KYC)
                print('V10 mixed scores:', [r['campaign_score'] for r in results])

    def test_url_is_parsed_once_without_network(self):
        from services.url_intelligence import analyze_url
        with patch('services.evidence_service.analyze_url', wraps=analyze_url) as parse, patch('services.analysis_service.extract_url_analysis') as extract, patch('socket.create_connection', side_effect=AssertionError('Network forbidden')):
            self.assertEqual(self.add('url', LINK).status_code, 200)
            parse.assert_called_once_with(LINK)
            extract.assert_not_called()
        self.llm.assert_called_once()

    def test_retry_each_type_is_idempotent(self):
        for kind, value in (('text', KYC), ('image', self.image()), ('audio', wav_bytes()), ('url', LINK)):
            key = str(uuid4())
            before = self.llm.call_count
            first = self.add(kind, value, key)
            second = self.add(kind, value, key)
            self.assertEqual(first.status_code, 200, first.text)
            self.assertEqual(first.json(), second.json())
            self.assertEqual(self.llm.call_count, before + 1)
        self.assertEqual(self.client.get(self.base).json()['evidence_count'], 4)
        self.ocr.assert_called_once(); self.stt.assert_called_once()

    def test_key_conflict_and_inflight_conflict(self):
        key = str(uuid4())
        self.add('text', KYC, key)
        self.assertEqual(self.add('text', OTP, key).status_code, 409)
        state = campaign_service._request_states[self.cid]
        state.busy = True
        try:
            self.assertEqual(self.add('text', OTP).status_code, 409)
            self.assertEqual(self.client.post(self.base + '/interactions', json={'type': 'text', 'content': OTP}).status_code, 409)
        finally: state.busy = False
        self.assertEqual(self.add('text', OTP).status_code, 200)

    def test_invalid_campaign_does_not_analyze(self):
        self.base = '/api/campaigns/expired'
        for kind, value in (('text', KYC), ('url', LINK), ('image', self.image()), ('audio', wav_bytes())):
            self.assertEqual(self.add(kind, value).status_code, 404)
        self.llm.assert_not_called(); self.ocr.assert_not_called(); self.stt.assert_not_called()

    def test_invalid_inputs_leave_campaign_unchanged(self):
        for kind, value in (('image', b'bad'), ('audio', b'bad'), ('url', 'javascript:alert(1)'), ('url', 'data:text/plain,bad'), ('url', 'file:///tmp/file')):
            self.assertEqual(self.add(kind, value).status_code, 422)
        self.assertEqual(self.add('image', b'x' * (MAX_IMAGE_BYTES + 1)).status_code, 413)
        self.assertEqual(self.add('audio', b'x' * (MAX_AUDIO_BYTES + 1)).status_code, 413)
        self.assertEqual(self.client.post(self.base + '/evidence/video').status_code, 404)
        self.assertEqual(self.client.post(self.base + '/evidence/image', files={'file': ('bad', b'bad', 'text/plain')}).status_code, 415)
        self.assertEqual(self.client.get(self.base).json()['evidence_count'], 0)
        self.llm.assert_not_called()

    def test_failure_can_retry_and_temporary_files_removed(self):
        key = str(uuid4())
        self.ocr.side_effect = ImageAnalysisError(503, 'OCR unavailable')
        self.assertEqual(self.add('image', self.image(), key).status_code, 503)
        self.ocr.side_effect = None
        self.assertEqual(self.add('image', self.image(), key).status_code, 200)
        def fail(wav, output):
            self.paths.append(wav.parent)
            raise AudioAnalysisError(503, 'Transcription unavailable')
        self.stt.side_effect = fail
        self.assertEqual(self.add('audio', wav_bytes()).status_code, 503)
        self.assertTrue(all(not path.exists() for path in self.paths))
        self.assertEqual(self.client.get(self.base).json()['evidence_count'], 1)

    def test_v5_fallback_and_legacy_route(self):
        response = self.client.post(self.base + '/interactions', json={'type': 'text', 'content': KYC})
        self.assertEqual(response.status_code, 200)
        item = response.json()['interactions'][0]
        self.assertFalse(item['analysis']['semantic']['available'])
        self.assertEqual(item['content'], KYC)
        self.assertEqual(item['order'], 1)
        self.assertEqual(self.add('text', OTP).json()['evidence_count'], 2)
