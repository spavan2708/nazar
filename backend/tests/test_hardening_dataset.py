"""Integrity checks for new research data without fitting models or touching production."""
import json
import unittest
from pathlib import Path
from pydantic import ValidationError
from ml.hardening_data import DATA, ROOT, ResearchExample, load, noise, NOISE_TYPES, normalized
from ml.dataset import sha


class HardeningDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.splits={name:load(name) for name in ('train','validation','test')}
        cls.manifest=json.loads((DATA/'manifest.json').read_text())

    def test_frozen_benchmark_unchanged(self):
        self.assertEqual(sha(ROOT/'eval_v2.json'),'aae98f6368793bb5ea0f754e1d0e7c06511cbcd7c2c98e16246dbba77d84508e')
        self.assertEqual(sha(ROOT/'train_v2.json'),'1e319c7e487fe9aee71fd2970c3daf0588f28a584b3ec33d2fc831a7000f31b4')

    def test_groups_and_normalized_text_do_not_cross_splits(self):
        seen_groups={};seen_text={};seen_ids=set()
        for split,rows in self.splits.items():
            for row in rows:
                self.assertNotIn(row['id'],seen_ids);seen_ids.add(row['id'])
                self.assertEqual(seen_groups.setdefault(row['cluster_id'],split),split)
                self.assertEqual(seen_text.setdefault(normalized(row['text']),split),split)
                self.assertEqual(row['cluster_id'],row['group'])
                if split!='train':
                    self.assertTrue(row['id'].startswith('h2-'))
                    self.assertIsNone(row['noise_type'])

    def test_parent_provenance_and_noise_limit(self):
        train={r['id']:r for r in self.splits['train']}
        noisy=[r for r in train.values() if r['noise_type']]
        self.assertLessEqual(len(noisy),.2*(len(train)-len(noisy)))
        for row in noisy:
            parent=train[row['parent_id']]
            self.assertEqual(row['cluster_id'],parent['cluster_id'])
            self.assertEqual(row['label'],parent['label'])
            self.assertEqual(row['signals'],parent['signals'])
            self.assertEqual(row['text'],noise(parent['text'],row['noise_type']))
        for rows in self.splits.values():
            ids={r['id']:r for r in rows}
            for row in rows:
                if row['translated_from']:
                    self.assertIn(row['translated_from'],ids)
                    self.assertEqual(row['group'],ids[row['translated_from']]['group'])

    def test_schema_rejects_unknown_signals_and_bad_labels(self):
        row=dict(self.splits['train'][0])
        for update in ({'signals':['MADE_UP_SIGNAL']},{'label':'maybe'},{'difficulty':'standard'},{'cluster_id':''}):
            with self.assertRaises(ValidationError):ResearchExample.model_validate(dict(row,**update))

    def test_quarantine_and_source_receipts(self):
        ids={r['id'] for rows in self.splits.values() for r in rows}
        self.assertFalse(ids & set(self.manifest['quality']['quarantined_ids']))
        for name,digest in self.manifest['source_hashes'].items():self.assertEqual(sha(DATA/name),digest)
        for kind in NOISE_TYPES:
            output=noise('Do not share your verification code; jaldi mat bhejo.',kind)
            self.assertIn('not',output.casefold());self.assertIn('mat',output.casefold())

    def test_safe_annotations_and_native_review_are_honest(self):
        for rows in self.splits.values():
            for row in rows:
                self.assertFalse(row['native_reviewed'])
                if row['id'].startswith('h2-') and row['label']=='safe':self.assertEqual(row['signals'],[])
                if row['safety_context']:self.assertEqual(row['label'],'safe')

    def test_finetuning_preserves_non_tensor_tokenizer_metadata(self):
        import torch
        from ml.finetune import to_device
        features={'input_ids':torch.tensor([[1,2]]),'task':'text','nested':None}
        moved=to_device(features,'cpu')
        self.assertTrue(torch.equal(moved['input_ids'],features['input_ids']))
        self.assertEqual(moved['task'],'text')
        self.assertIsNone(moved['nested'])

    def test_frozen_loader_checks_fingerprint(self):
        from unittest.mock import patch
        from ml.hardening_data import load_frozen_v2
        self.assertEqual(len(load_frozen_v2()),90)
        with patch('ml.hardening_data.sha',return_value='different'):
            with self.assertRaises(ValueError):load_frozen_v2()
