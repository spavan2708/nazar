import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import numpy as np
from ml import neighbors
from schemas.analysis import MLAnalysis, TextAnalysisResponse
from schemas.semantic import SemanticAnalysis
from services.risk_fusion import fuse_risk
from services.text_analyzer import analyze_text


class AgreementTests(unittest.TestCase):
    def result(self, text, score=None, llm=None):
        return fuse_risk(analyze_text(text), MLAnalysis(available=score is not None, scam_probability=score), llm)

    def test_statuses_and_availability(self):
        cases = [
            ('Send me the OTP immediately.', .91, SemanticAnalysis(available=True, risk_score=.95), 'STRONG_AGREEMENT'),
            ('Send me the OTP immediately.', .91, None, 'PARTIAL_AGREEMENT'),
            ('Send me the OTP immediately.', None, None, 'RULES_ONLY'),
            ('Hello, see you at lunch.', .72, None, 'ML_ONLY'),
            ('Hello, see you at lunch.', None, SemanticAnalysis(available=True, risk_score=.9), 'LLM_ONLY'),
            ('Hello, see you at lunch.', .1, None, 'INSUFFICIENT_EVIDENCE'),
            ('Never share your OTP with anyone.', .78, None, 'CONFLICTING'),
        ]
        for text, score, llm, expected in cases:
            with self.subTest(expected=expected):
                result=self.result(text, score, llm)
                self.assertEqual(result.intelligence.agreement.status, expected)
                self.assertEqual(result.intelligence.ml.available, score is not None)
                self.assertEqual(result.intelligence.llm.available, llm is not None)
        warning=self.result('Never share your OTP with anyone.', .78)
        self.assertTrue(warning.intelligence.deterministic.safety_warning)
        self.assertFalse(warning.intelligence.deterministic.suspicious)
        self.assertEqual(warning.score,35)

    def test_metadata_does_not_change_scoring(self):
        for text in ('Send me the OTP immediately.', 'Never share your OTP with anyone.', 'Hello.'):
            for score in (.1, .65, .8):
                actual=self.result(text,score).model_dump(exclude={'intelligence'})
                with patch('services.risk_fusion.describe_sources',return_value=None):
                    self.assertEqual(actual,self.result(text,score).model_dump(exclude={'intelligence'}))

    def test_old_payload_and_public_fields(self):
        old=dict(score=0,risk_level='low',signals=[],explanation='Hello',recommended_action='None')
        self.assertIsNone(TextAnalysisResponse(**old).intelligence)
        payload=self.result('Hello.',.7).model_dump(mode='json')
        self.assertIn('scam_probability',payload['ml'])
        self.assertNotIn('semantic_neighbors',payload['ml'])
        self.assertNotIn('context',payload)


class NeighborTests(unittest.TestCase):
    def setUp(self):
        neighbors.clear_reference_cache()
        self.env=patch.dict('os.environ',{'ML_EXPLANATIONS_ENABLED':'true'});self.env.start()
        self.rows=json.loads((neighbors.DATA/'train_v2.json').read_text())
        self.model=Mock()
        self.model.encode.return_value=np.array([[1., .1] if r['label']=='scam' else [.1,1.] for r in self.rows])

    def tearDown(self):
        self.env.stop();neighbors.clear_reference_cache()

    def test_labels_ranges_cache_and_projection(self):
        for query in ([1.,0.],[0.,1.]):
            result=neighbors.explain_neighbors(self.model,query,'v2')
            self.assertTrue(result.available)
            for label,items in [('scam',result.suspicious),('safe',result.safe)]:
                self.assertEqual(len(items),2)
                for item in items:
                    self.assertIn(item.text,[r['text'] for r in self.rows if r['label']==label])
                    self.assertTrue(-1<=item.similarity<=1)
                    self.assertEqual(set(item.model_dump()),{'text','similarity','language','category'})
        self.model.encode.assert_called_once()

    def test_disabled_and_v1_skip_encoding(self):
        with patch.dict('os.environ',{'ML_EXPLANATIONS_ENABLED':'false'}):
            self.assertFalse(neighbors.explain_neighbors(self.model,[1,0],'v2').available)
        self.assertFalse(neighbors.explain_neighbors(self.model,[1,0],'v1').available)
        self.model.encode.assert_not_called()

    def test_bad_index_and_query_fail_closed(self):
        self.model.encode.return_value=np.array([[float('nan'),0]]*len(self.rows))
        self.assertFalse(neighbors.explain_neighbors(self.model,[1,0],'v2').available)
        self.model.encode.side_effect=RuntimeError('private details')
        self.assertFalse(neighbors.explain_neighbors(self.model,[1,0],'v2').available)

    def test_reference_provenance_mismatch_skips_encoding(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'train_v2.json').write_text('[]')
            (root/'v2_manifest.json').write_text('{"train_v2.json":"wrong"}')
            with patch.object(neighbors,'DATA',root):
                self.assertFalse(neighbors.explain_neighbors(self.model,[1,0],'v2').available)
        self.model.encode.assert_not_called()

    def test_disabled_preserves_prediction(self):
        from ml.classifier import predict_scam_probability
        with patch.dict('os.environ',{'NAZAR_ML_VERSION':'v2'}):
            on=predict_scam_probability('Send me the OTP immediately.')
            with patch.dict('os.environ',{'ML_EXPLANATIONS_ENABLED':'false'}):
                off=predict_scam_probability('Send me the OTP immediately.')
        self.assertTrue(on.available)
        self.assertTrue(on.semantic_neighbors.available)
        self.assertFalse(off.semantic_neighbors.available)
        self.assertEqual(on.scam_probability,off.scam_probability)
        # The frozen model actually misses this explicit request (~0.307).
        # Explanations must reveal that limitation, never force a prediction.
        self.assertLess(on.scam_probability,.65)
        result=fuse_risk(analyze_text('Send me the OTP immediately.'),on)
        self.assertEqual(result.intelligence.agreement.status,'RULES_ONLY')
