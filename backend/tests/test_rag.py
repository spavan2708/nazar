import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import numpy as np
from pydantic import ValidationError
from rag import retriever
from rag.build_index import build_index
from rag.knowledge import load_documents, chunk_documents
from rag.schemas import Grounding, KnowledgeDocument, trusted_url
from schemas.analysis import MLAnalysis, TextAnalysisResponse
from schemas.semantic import SemanticAnalysis
from services.analysis_service import analyze_text
from services.text_analyzer import analyze_text as rules


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict('os.environ', {'RAG_ENABLED':'true'})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def retrieve(self, text):
        return retriever.retrieve_guidance(text, rules(text).signal_codes)

    def test_targeted_offline_retrieval(self):
        for text, topic in [
            ('Send me the OTP immediately.', 'otp'),
            ('Install AnyDesk so I can control your phone.', 'remote_access'),
            ('Your bank KYC expires today. Click this link immediately.', 'banking_kyc'),
        ]:
            with self.subTest(topic=topic), patch('socket.socket.connect', side_effect=AssertionError('No runtime network')):
                result=self.retrieve(text)
                self.assertTrue(result.available)
                self.assertIn(topic,{t for r in result.results for t in r.topics})
                self.assertLessEqual(len(result.results),3)
                self.assertEqual(len(result.results),len({r.source_url for r in result.results}))
                self.assertTrue(all(-1 <= r.similarity <= 1 for r in result.results))

    def test_benign_and_generic_urgency_abstain(self):
        for text in ('Hello, see you at lunch.', 'Please bring milk home.', 'The meeting starts immediately.'):
            result=self.retrieve(text)
            self.assertTrue(result.available)
            self.assertEqual(result.results,[])

    def test_disabled_and_missing_index(self):
        with patch.dict('os.environ',{'RAG_ENABLED':'false'}), patch.object(retriever,'load_index') as load:
            self.assertFalse(self.retrieve('Send OTP').available)
            load.assert_not_called()
        with tempfile.TemporaryDirectory() as directory, patch.object(retriever,'INDEX_DIR',Path(directory)):
            self.assertFalse(self.retrieve('Send OTP').available)

    def test_index_cache_and_no_reference_reencoding(self):
        retriever.clear_index_cache()
        with patch.object(retriever,'model_fingerprint',wraps=retriever.model_fingerprint) as fingerprint:
            first=retriever.load_index()
            self.assertIs(first,retriever.load_index())
            fingerprint.assert_called_once()
        model=Mock()
        model.encode.return_value=np.ones((1,384))
        with patch.object(retriever,'get_embedding_model',return_value=model):
            self.retrieve('Send OTP')
            self.retrieve('Install AnyDesk')
        self.assertEqual(model.encode.call_count,2)
        self.assertTrue(all(len(c.args[0])==1 for c in model.encode.call_args_list))

    def test_low_similarity_and_ambiguous_semantics_abstain(self):
        docs,chunks,_=retriever.load_index()
        matrix=np.zeros((len(chunks),384),dtype=np.float32);matrix[:,0]=1
        model=Mock();model.encode.return_value=np.eye(384,dtype=np.float32)[1:2]
        with patch.object(retriever,'load_index',return_value=(docs,chunks,matrix)), patch.object(retriever,'get_embedding_model',return_value=model):
            self.assertEqual(self.retrieve('What does OTP mean?').results,[])
            model.encode.return_value=np.eye(384,dtype=np.float32)[:1]
            self.assertEqual(self.retrieve('Hi there.').results,[])  # high scores but no margin

    def test_stage_only_and_campaign_similarity_is_not_fabricated(self):
        with patch.object(retriever,'get_embedding_model') as model:
            result=retriever.retrieve_guidance('',[],['REMOTE_ACCESS'])
            self.assertEqual(result.results[0].topics,['remote_access'])
            self.assertIsNone(result.results[0].similarity)
            self.assertEqual(result.results[0].matched_stages,['REMOTE_ACCESS'])
            model.assert_not_called()

    def test_invalid_query_fails_closed(self):
        model=Mock();model.encode.return_value=np.full((1,384),np.nan)
        with patch.object(retriever,'get_embedding_model',return_value=model):
            self.assertFalse(self.retrieve('Send OTP').available)


class CurationTests(unittest.TestCase):
    def test_coverage_chunking_and_source_validation(self):
        docs,_=load_documents();chunks=chunk_documents(docs)
        self.assertEqual(len(docs),10)
        self.assertEqual(len(chunks),10)
        self.assertEqual(len({t for d in docs for t in d.topics}),10)
        for doc in docs:
            self.assertEqual(' '.join(c.text for c in chunks if c.source_id==doc.id),doc.content)
        for url in ('https://evil.example/x','javascript:alert(1)','https://sbi.co.in.evil.example/','https://user@sbi.co.in/x','http://sbi.co.in/x'):
            with self.assertRaises(ValueError): trusted_url(url)
        bad=docs[0].model_dump();bad['signal_codes']=['FAKE_SIGNAL']
        with self.assertRaises(ValidationError): KnowledgeDocument.model_validate(bad)

    def test_reproducible_index_and_tamper_fallback(self):
        model=Mock();model.encode.return_value=np.ones((10,384),dtype=np.float32)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch('rag.build_index.get_embedding_model',return_value=model):
                one=build_index(root);two=build_index(root)
            self.assertEqual(one,two)
            with patch.object(retriever,'INDEX_DIR',root):
                retriever.clear_index_cache()
                self.assertEqual(len(retriever.load_index()[1]),10)
                (root/'vectors.npy').write_bytes(b'corrupt')
                self.assertFalse(retriever.retrieve_guidance('Send OTP',['OTP_REQUEST']).available)
        retriever.clear_index_cache()


class IntegrationTests(unittest.TestCase):
    def test_score_invariance_and_one_semantic_call(self):
        with patch('services.analysis_service.predict_scam_probability',return_value=MLAnalysis(available=False)), patch('services.analysis_service.analyze_semantics',return_value=SemanticAnalysis(available=False)) as semantic:
            for text in ('Send me the OTP immediately.','Never share your OTP with anyone.','Hello, see you at lunch.'):
                with patch.dict('os.environ',{'RAG_ENABLED':'true'}): on=analyze_text(text)
                with patch.dict('os.environ',{'RAG_ENABLED':'false'}): off=analyze_text(text)
                self.assertEqual(on.model_dump(exclude={'grounding', 'orchestration', 'timings_ms'}),off.model_dump(exclude={'grounding', 'orchestration', 'timings_ms'}))
                self.assertFalse(off.grounding.available)
                if 'OTP' in text:
                    self.assertTrue(on.grounding.results)
            self.assertEqual(semantic.call_count,6)  # exactly once per analysis

    def test_provider_receives_no_guidance_and_is_called_once(self):
        from schemas.semantic import SemanticProviderOutput
        provider=Mock(name='existing-provider')
        provider.name='test';provider.model_version='test';provider.is_mock=True
        provider.analyze.return_value=SemanticProviderOutput(risk_score=.1,explanation='Test')
        with patch('services.llm.semantic_analyzer.configured_provider',return_value=provider), patch('services.analysis_service.predict_scam_probability',return_value=MLAnalysis(available=False)):
            result=analyze_text('Send me the OTP immediately.')
        self.assertIsNotNone(result.grounding)
        provider.analyze.assert_called_once()
        self.assertNotIn('State Bank',provider.analyze.call_args.args[1])

    def test_legacy_payload_and_api_privacy(self):
        old=TextAnalysisResponse(score=0,risk_level='low',signals=[],explanation='Hi',recommended_action='None')
        self.assertIsNone(old.grounding)
        from fastapi.testclient import TestClient
        from main import app
        with patch.dict('os.environ',{'RAG_ENABLED':'true','LLM_ENABLED':'false'}):
            response=TestClient(app).post('/api/analyze/text',json={'text':'Send me the OTP immediately.'})
        self.assertEqual(response.status_code,200)
        data=response.json()
        self.assertTrue(data['grounding']['results'])
        self.assertIn('ml',data)
        grounding=json.dumps(data['grounding'])
        for private in ('embedding','vectors','provenance_note','API_KEY','/Users/'):
            self.assertNotIn(private,grounding)

    def test_campaign_deduplication_and_score_invariance(self):
        from services import campaign_service
        from schemas.evidence import EvidenceDraft, EvidenceType
        campaigns=[]
        for enabled in ('true','false'):
            with patch.dict('os.environ',{'RAG_ENABLED':enabled}):
                campaign=campaign_service.create_campaign()
                for text in ('Send me the OTP immediately.','Send me the OTP immediately.','Install AnyDesk so I can control your phone.'):
                    result=rules(text)
                    campaign=campaign_service.add_evidence(campaign.campaign_id,lambda: EvidenceDraft(type=EvidenceType.TEXT,content=text,analysis=result))
                campaigns.append(campaign)
        self.assertEqual(campaigns[0].campaign_score,campaigns[1].campaign_score)
        self.assertEqual(campaigns[0].stages,campaigns[1].stages)
        results=campaigns[0].grounding.results
        self.assertTrue(results)
        self.assertEqual(len(results),len({r.source_url for r in results}))
        self.assertTrue(all(r.similarity is None for r in results))
