"""Reproducible audit of legacy split overlap; does not edit or relabel datasets."""
import argparse
import json
from pathlib import Path
import numpy as np
from ml.dataset import load_split, quality
from ml.embeddings import get_embedding_model
from ml.hardening_data import legacy_audit


def run(output):
    if output.exists():raise FileExistsError('Audit output already exists')
    splits={s:load_split(s) for s in ('train','validation','test')}
    rows=sum(splits.values(),[])
    encoder=get_embedding_model()
    X=np.asarray(encoder.encode([r['text'] for r in rows],normalize_embeddings=True,show_progress_bar=False))
    report=dict(datasets=legacy_audit(),split_quality=quality(splits,X),
        notes=['The 150 v2 training rows are included in the later 260-row development corpus; do not add these counts together.',
               'The 48-row v1 corpus used a historical 36/12 split; language/category provenance was not recorded per row.',
               'Legacy category and text-noise counts are proxies, not retroactively verified annotations.',
               'Semantic cosine flags are not proof of duplicate meaning; multilingual encoder collapse can create false matches.'])
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:len(report['split_quality'][k]) for k in ('normalized_duplicate_records','blocking_cross_split_overlaps','semantic_review_candidates')}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
