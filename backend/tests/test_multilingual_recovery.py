import unittest,json
import numpy as np
from ml.recovery import DATA,recovery_split,objective,sampling_weights
from ml.hardening_data import normalized
from ml.dataset import sha
from evaluation.multilingual_recovery import hybrid


class RecoveryTests(unittest.TestCase):
    def test_recovery_split_integrity_and_quarantine(self):
        manifest=json.loads((DATA/'manifest.json').read_text())
        self.assertEqual(sha(DATA/'pairs.tsv'),manifest['source_hash'])
        train,valid=recovery_split('train'),recovery_split('validation')
        self.assertFalse({r['group'] for r in train}&{r['group'] for r in valid})
        self.assertFalse({r['group'] for r in train+valid}&set(manifest['quarantined_groups']))
        self.assertFalse({normalized(r['text']) for r in train}&{normalized(r['text']) for r in valid})
        self.assertFalse(json.loads((DATA/'split-audit.json').read_text())['blocking_cross_split_overlaps'])
        self.assertFalse(json.loads((DATA/'split-audit.json').read_text())['semantic_review_candidates'])
        self.assertTrue(all(not r['native_reviewed'] for r in train+valid))

    def test_objective_exposes_minority_failure(self):
        rows=[dict(language='English',label='scam',group='en') for _ in range(50)]+[dict(language='Tamil',label='scam',group='ta')]
        r=objective(rows,np.array([.9]*50+[.1]))
        self.assertGreater(r['overall']['f1'],.9)
        self.assertEqual(r['worst_recall'],0)
        self.assertEqual(r['macro_f1'],.5)

    def test_balancing_increases_minority_weight_without_unbounded_weights(self):
        rows=[dict(language='English',label='scam',group='en') for _ in range(20)]+[dict(language='Tamil',label='scam',group='ta')]
        w=sampling_weights(rows,'language_cluster')
        self.assertGreater(w[-1],w[0]);self.assertLessEqual(w.max(),4.)
        np.testing.assert_equal(sampling_weights(rows,'uniform'),np.ones(21))

    def test_offline_hybrid_requires_script_and_model_evidence(self):
        tamil='உங்கள் கணக்கை பாதுகாப்பாக வைத்திருங்கள்'
        rows=[dict(text=tamil),dict(text=tamil),dict(text='unga account safe ah irukkattum')]
        p=hybrid(rows,np.array([.2,.2,.2]),np.array([.9,.7,.9]))
        np.testing.assert_allclose(p,[.9,.2,.2])
