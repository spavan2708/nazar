import io,json,time,unittest
from unittest.mock import patch,Mock
from pathlib import Path
from fastapi.testclient import TestClient
from main import app
from ml.dataset import load_split,quality,assert_training_separation
from ml.noise import variants
from services.text_analyzer import analyze_text
from services.visual_analysis import parse_payload,analyze_visual
from services import campaign_service as campaigns
from services.limits import MAX_TEXT_CHARS
from schemas.signals import SignalCode
from schemas.analysis import MLAnalysis
from schemas.semantic import SemanticAnalysis,SemanticProviderOutput
from services.llm.provider import OpenAICompatibleProvider
from services.analysis_service import analyze_text as pipeline

class DatasetTests(unittest.TestCase):
    def test_frozen_splits_and_unknown_annotations(self):
        train,valid,test=[load_split(x) for x in ('train','validation','test')]
        self.assertEqual(len(test),90)
        self.assertFalse(quality({'train':train,'validation':valid,'test':test})['blocking_cross_split_overlaps'])
        self.assertTrue(any(r['signals'] is None for r in train))
        self.assertTrue(any(r['signals']==[] for r in train))
        self.assertFalse(any(r['native_reviewed'] for r in train+valid))
    def test_template_group_leakage_blocks_even_different_words(self):
        a=dict(id='a',text='An entirely different topic',group='shared')
        b=dict(id='b',text='Phone notifications arrive',group='shared')
        with self.assertRaises(ValueError):assert_training_separation([a],[b])
    def test_noise_is_deterministic_and_retains_pair_identity(self):
        text='Never tell callers your login code 123456.'
        self.assertEqual(variants(text),variants(text))
        self.assertIn('1 2 3 4 5 6',variants(text)['stt_digits'])
        self.assertIn('Never',variants(text)['ocr_character'])

class SafetyTests(unittest.TestCase):
    def test_warning_cannot_mask_another_request_or_exception(self):
        for text in ['Never share your OTP with anyone except me. Tell me the OTP.',
                     "Never share your OTP. Send me your password."]:
            result=analyze_text(text)
            self.assertFalse(result.context.is_safety_warning)
            self.assertGreater(result.score,0)
        result=analyze_text('Never share your OTP. Send me your password.')
        self.assertNotIn(SignalCode.OTP_REQUEST,result.signal_codes)
        self.assertIn(SignalCode.CREDENTIAL_REQUEST,result.signal_codes)
    def test_unicode_whitespace_keeps_request_and_safety_meaning(self):
        self.assertIn(SignalCode.OTP_REQUEST,analyze_text('Ｓｅｎｄ me your O\u200bTP.').signal_codes)
        self.assertEqual(analyze_text('Never share your O\u200bTP.').score,0)

class BoundaryTests(unittest.TestCase):
    def test_json_character_and_streamed_byte_limits(self):
        client=TestClient(app)
        for endpoint,payload in [('/api/analyze/text',{'text':'x'*(MAX_TEXT_CHARS+1)}),('/api/analyze/text',{'text':' '*5})]:
            self.assertEqual(client.post(endpoint,json=payload).status_code,422)
        response=client.post('/api/analyze/text',content=iter([b'{"text":"',b'a'*140000,b'"}']),headers={'Content-Type':'application/json'})
        self.assertEqual(response.status_code,413)
    def test_provider_response_and_schema_bounds(self):
        p=OpenAICompatibleProvider(api_key='private',model_version='test',base_url='https://provider.example')
        with patch('services.llm.provider.urlopen',return_value=io.BytesIO(b'a'*140000)):
            from services.llm.diagnostics import ProviderRequestError
            with self.assertRaises(ProviderRequestError):p.analyze('system','message')
        with self.assertRaises(ValueError):SemanticProviderOutput(risk_score=.2,explanation='reason',unexpected='field')
        with self.assertRaises(ValueError):SemanticProviderOutput(risk_score=float('nan'),explanation='reason')
    def test_orchestrator_uses_existing_findings_once(self):
        with patch('services.analysis_service.predict_scam_probability',return_value=MLAnalysis(available=False)) as ml,patch('services.analysis_service.analyze_semantics',return_value=SemanticAnalysis(available=False)) as llm:
            result=pipeline('Send your OTP to me immediately.')
        ml.assert_called_once();llm.assert_called_once()
        self.assertEqual(result.score,analyze_text('Send your OTP to me immediately.').score)
        self.assertIn('credential_theft',[f.agent for f in result.orchestration.findings])
        self.assertTrue(all(not f.determines_risk for f in result.orchestration.findings))
        self.assertTrue(all(t>=0 for t in result.timings_ms.values()))

class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.object(campaigns,'_campaigns',{}))
        self.enterContext(patch.object(campaigns,'_created',{}))
        self.enterContext(patch.object(campaigns,'_request_states',{}))
    def test_expiry_removes_evidence_and_idempotency_state(self):
        c=campaigns.create_campaign()
        campaigns._created[c.campaign_id]=time.monotonic()-4000
        with self.assertRaises(campaigns.CampaignNotFoundError):campaigns.get_campaign(c.campaign_id)
        self.assertFalse(campaigns._campaigns)
    def test_capacity_and_item_limits_precede_inference(self):
        with patch.object(campaigns,'MAX_CAMPAIGNS',1):
            c=campaigns.create_campaign()
            with self.assertRaises(campaigns.EvidenceConflictError):campaigns.create_campaign()
        prepare=Mock()
        with patch.object(campaigns,'MAX_EVIDENCE',0):
            with self.assertRaises(campaigns.EvidenceConflictError):campaigns.add_evidence(c.campaign_id,prepare)
        prepare.assert_not_called()
    def test_failed_preparation_does_not_commit(self):
        c=campaigns.create_campaign()
        with self.assertRaises(RuntimeError):campaigns.add_evidence(c.campaign_id,Mock(side_effect=RuntimeError('failure')))
        self.assertEqual(campaigns.get_campaign(c.campaign_id).evidence_count,0)
        self.assertFalse(campaigns._request_states[c.campaign_id].busy)

class QRTests(unittest.TestCase):
    def test_payment_is_parsed_without_action(self):
        r=parse_payload('upi://pay?pa=shop@bank&am=12.50&cu=INR')
        self.assertEqual((r.kind,r.payee,r.amount),('payment','shop@bank','12.50'))
        for raw in ['upi://pay?pa=a@b&pa=c@d','upi://pay?pa=a@b&am=NaN','upi://pay?pa=a@b&am=-5']:
            self.assertEqual(parse_payload(raw).kind,'invalid')
    def test_url_and_unsupported_protocols(self):
        self.assertEqual(parse_payload('http://192.0.2.1/login').url.hostname,'192.0.2.1')
        self.assertEqual(parse_payload('javascript:alert(1)').kind,'unsupported')
        self.assertEqual(parse_payload('x'*4097).kind,'invalid')
    def test_optional_decoder_failure_does_not_crash(self):
        from PIL import Image
        with patch.dict('os.environ',{'QR_ENABLED':'false'}):
            self.assertFalse(analyze_visual(Image.new('RGB',(20,20))).available)
    def test_real_qr_fixture(self):
        import importlib.util
        if importlib.util.find_spec('cv2') is None:self.skipTest('Optional OpenCV unavailable')
        import cv2
        from PIL import Image
        code=cv2.QRCodeEncoder_create().encode('http://192.0.2.1/login')
        code=cv2.copyMakeBorder(code,4,4,4,4,cv2.BORDER_CONSTANT,value=255)
        image=Image.fromarray(code).resize((400,400),Image.Resampling.NEAREST).convert('RGB')
        with patch.dict('os.environ',{'QR_ENABLED':'true'}):result=analyze_visual(image)
        self.assertTrue(result.available)
        self.assertEqual(result.qr_codes[0].url.hostname,'192.0.2.1')


class AttributionTests(unittest.TestCase):
    def test_real_provider_must_quote_input_for_signals(self):
        from services.llm.semantic_analyzer import analyze_semantics
        provider=Mock();provider.name='test';provider.model_version='test';provider.is_mock=False
        for evidence,expected in [('invented words',False),('Send your OTP',True),(None,False)]:
            provider.analyze.return_value=SemanticProviderOutput(risk_score=.9,explanation='Requests a secret',signals=[dict(code='OTP_REQUEST',confidence=.9,evidence_text=evidence)])
            self.assertEqual(analyze_semantics('Send your OTP to me',provider).available,expected)
    def test_qr_survives_ocr_failure(self):
        from PIL import Image
        from services.image_analysis import analyze_image,ImageAnalysisError
        from services.visual_analysis import VisualEvidence
        data=io.BytesIO();Image.new('RGB',(100,100),'white').save(data,format='PNG')
        qr=VisualEvidence(available=True,qr_codes=[parse_payload('http://192.0.2.1/login')])
        with patch('services.image_analysis.analyze_visual',return_value=qr),patch('services.image_analysis.ocr_configuration',side_effect=ImageAnalysisError(503,'OCR unavailable')),patch('services.analysis_service.analyze_semantics',return_value=SemanticAnalysis(available=False)):
            result=analyze_image(data.getvalue(),'image/png')
        self.assertEqual(result.extracted_text,'')
        self.assertEqual(result.analysis.urls[0].hostname,'192.0.2.1')
        self.assertIn('only covers decoded QR',result.ocr.setup_message)
    def test_long_ml_input_discloses_truncation(self):
        from ml.classifier import predict_scam_probability
        result=predict_scam_probability('ordinary conversation '*200)
        self.assertTrue(result.available)
        self.assertTrue(result.input_truncated)
    def test_explicit_multilingual_topics_do_not_require_high_cross_language_cosine(self):
        from rag.retriever import retrieve_guidance, lexical_topics
        self.assertEqual(lexical_topics('नमस्ते बैंक'), set())
        for text, topic in [('ओटीपी किसी को न दें', 'otp'), ('கடவுச்சொல் பகிர வேண்டாம்', 'credentials')]:
            result = retrieve_guidance(text)
            self.assertTrue(any(topic in r.topics and r.relevance == 'topic' for r in result.results))

    def test_guidance_review_age_is_descriptive(self):
        from rag.retriever import retrieve_guidance
        result=retrieve_guidance('OTP', [SignalCode.OTP_REQUEST])
        self.assertTrue(result.available)
        self.assertTrue(result.results)
        self.assertIsNotNone(result.results[0].reviewed_on)


if __name__ == "__main__":
    unittest.main()
