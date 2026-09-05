import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from ml import classifier
from ml.v2_data import DATA, load_frozen, validate, validate_split, normalized
from ml.v2_experiments import folds, select, probability, metrics
from services import risk_fusion


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train, cls.evaluation, cls.hashes = load_frozen()

    def test_sizes_balance_languages_and_freeze(self):
        self.assertEqual(len(self.train),150); self.assertEqual(len(self.evaluation),90)
        for rows in (self.train,self.evaluation):
            self.assertEqual(sum(r['label']=='scam' for r in rows),len(rows)//2)
            self.assertEqual({r['language'] for r in rows},{'English','Hindi','Tamil','Hinglish','Tanglish','Mixed'})
        self.assertFalse({normalized(r['text']) for r in self.train} & {normalized(r['text']) for r in self.evaluation})

    def test_invalid_data_rejected(self):
        for key,value in [('label','unknown'),('text',' '),('language','unknown'),('group','')]:
            records=copy.deepcopy(self.train);records[0][key]=value
            with self.assertRaises(ValueError): validate(records)
        with self.assertRaises(ValueError): validate(self.train+[self.train[0]])
        with self.assertRaises(ValueError): validate([])

    def test_exact_and_near_overlap_rejected(self):
        for text in (self.train[0]['text'],self.train[0]['text']+' Please.'):
            evaluation=copy.deepcopy(self.evaluation);evaluation[0]['text']=text
            with self.assertRaises(ValueError): validate_split(self.train,evaluation)

    def test_translation_groups_never_cross_folds(self):
        y=np.array([r['label']=='scam' for r in self.train]);groups=np.array([r['group'] for r in self.train])
        for train,valid in folds(y,groups):
            self.assertFalse(set(groups[train]) & set(groups[valid]))
            for inner_train,inner_valid in folds(y[train],groups[train],3):
                self.assertFalse(set(groups[train][inner_train]) & set(groups[train][inner_valid]))


class ExperimentTests(unittest.TestCase):
    def test_training_is_deterministic_including_calibration(self):
        rng=np.random.default_rng(123);X=rng.normal(size=(60,8));y=np.array([0,1]*30);X[:,0]+=y*2;groups=np.arange(60)
        specs=[{'kind':'lr','C':1.,'class_weight':None},{'kind':'svm_sigmoid','C':1.,'class_weight':'balanced'}]
        first,win1,results1=select(X,y,groups,specs)
        second,win2,results2=select(X,y,groups,specs)
        self.assertEqual(win1['spec'],win2['spec'])
        np.testing.assert_allclose(probability(first,X),probability(second,X),atol=1e-12)
        self.assertEqual(results1,results2)

    def test_metrics_and_single_class_groups(self):
        m=metrics([0,0,1,1],[.1,.9,.2,.8])
        self.assertEqual(m['confusion_matrix'],[[1,1],[1,1]])
        self.assertEqual(m['f1'],.5)
        self.assertIsNone(metrics([0,0],[.2,.3])['roc_auc'])

    def test_thresholds_unchanged(self):
        self.assertEqual(risk_fusion.ML_MODERATE_THRESHOLD,.65)
        self.assertEqual(risk_fusion.ML_HIGH_THRESHOLD,.80)


class ArtifactTests(unittest.TestCase):
    def tearDown(self):
        classifier._load_model_bundle.cache_clear()

    def test_v1_v2_loading_and_multilingual_probabilities(self):
        for version in ('v1','v2'):
            with patch.dict('os.environ',{'NAZAR_ML_VERSION':version}):
                for text in ('Tell me the code from your bank.', 'आपका ओटीपी बताइए।', 'உங்கள் ரகசிய எண்ணை கூறுங்கள்.', 'OTP mujhe batao.', 'Unga OTP sollunga.'):
                    result=classifier.predict_scam_probability(text)
                    self.assertTrue(result.available)
                    self.assertEqual(result.model_version,version)
                    self.assertGreaterEqual(result.scam_probability,0)
                    self.assertLessEqual(result.scam_probability,1)

    def test_missing_and_corrupt_v2_fallback(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(classifier,'V2_DIR',Path(directory)), patch.dict('os.environ',{'NAZAR_ML_VERSION':'v2'}):
            classifier._load_model_bundle.cache_clear()
            self.assertFalse(classifier.predict_scam_probability('Hello').available)
            (Path(directory)/'classifier.joblib').write_bytes(b'not a classifier')
            (Path(directory)/'metadata.json').write_text('{}')
            self.assertFalse(classifier.predict_scam_probability('Hello').available)
            # A matching digest alone cannot make malformed classifier bytes usable.
            (Path(directory)/'metadata.json').write_text(json.dumps({'model_version':'v2','classifier_sha256':hashlib.sha256(b'not a classifier').hexdigest()}))
            self.assertFalse(classifier.predict_scam_probability('Hello').available)

    def test_auto_retains_v1_when_v2_missing(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(classifier,'V2_DIR',Path(directory)), patch.dict('os.environ',{'NAZAR_ML_VERSION':'auto'}):
            result=classifier.predict_scam_probability('Hello')
            self.assertTrue(result.available);self.assertEqual(result.model_version,'v1')

    def test_v2_campaign_uses_existing_formula(self):
        from services import campaign_service
        from services.analysis_service import analyze_text
        from schemas.evidence import EvidenceDraft, EvidenceType
        from schemas.semantic import SemanticAnalysis
        with patch.dict('os.environ', {'NAZAR_ML_VERSION':'v2'}), patch('services.analysis_service.analyze_semantics', return_value=SemanticAnalysis(available=False)):
            campaign=campaign_service.create_campaign()
            for text in ('Your KYC expires today. Verify immediately.', 'Install this screen-sharing app so I can help you.'):
                result=analyze_text(text)
                self.assertTrue(result.ml.available)
                self.assertEqual(result.ml.model_version,'v2')
                campaign=campaign_service.add_evidence(campaign.campaign_id, lambda: EvidenceDraft(type=EvidenceType.TEXT,content=text,analysis=result))
            self.assertEqual(campaign.campaign_score,campaign_service._calculate_campaign_score(campaign.interactions))

    def test_bad_version_does_not_break_analysis(self):
        with patch.dict('os.environ',{'NAZAR_ML_VERSION':'unsupported'}):
            self.assertFalse(classifier.predict_scam_probability('Hello').available)

    def test_saved_selection_precedes_heldout_and_matches_artifact(self):
        path=classifier.V2_DIR
        selection=json.loads((path/'selection.json').read_text())
        final=json.loads((path/'metadata.json').read_text())
        self.assertNotIn('evaluation_metrics',selection)
        self.assertEqual(selection['selected'],final['selected'])
        self.assertEqual(selection['classifier_sha256'],final['classifier_sha256'])
