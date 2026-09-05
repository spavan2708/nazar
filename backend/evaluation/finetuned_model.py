"""Evaluate a completed local encoder checkpoint; never select or deploy on test."""
import argparse
import json
import time
from pathlib import Path
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from ml.hardening_data import ROOT, DATA, load, noise, NOISE_TYPES, load_frozen_v2
from ml.dataset import sha
from ml.hardening_experiments import measure


def run(checkpoint, output):
    if output.exists():raise FileExistsError('Evaluation output already exists')
    metadata=json.loads((checkpoint/'metadata.json').read_text())
    if metadata['dataset_manifest_sha256']!=sha(DATA/'manifest.json'):raise ValueError('Dataset mismatch')
    torch.set_num_threads(4)
    model=SentenceTransformer(str(checkpoint/'encoder'),local_files_only=True,device='cpu')
    head=torch.nn.Linear(model.get_sentence_embedding_dimension(),1)
    head.load_state_dict(torch.load(checkpoint/'head.pt',map_location='cpu',weights_only=True))
    head.eval();model.eval()
    def score(rows):
        with torch.no_grad():
            vectors=model.encode([r['text'] for r in rows],normalize_embeddings=False,convert_to_tensor=True,show_progress_bar=False)
            return torch.sigmoid(head(vectors).squeeze(-1)).numpy()
    from tests.implicit_code_cases import ATTACKS,SAFE
    tests={'new_grouped_test':load('test'),'frozen_v2':load_frozen_v2(),
        'implicit_family':[dict(id=f'family-{i}',text=t,label='scam' if i<len(ATTACKS) else 'safe',language='Unknown',category='implicit' if i<len(ATTACKS) else 'safety',safety_context=i>=len(ATTACKS)) for i,t in enumerate(ATTACKS+SAFE)],
        'adversarial':json.loads((ROOT.parents[1]/'evaluation/hardening/adversarial_cases.json').read_text())}
    evaluation={}
    for name,rows in tests.items():
        for row in rows:row.setdefault('language','Unknown');row.setdefault('category','Unknown')
        evaluation[name]=measure(rows,score(rows))
    noise_results={}
    for kind in NOISE_TYPES:
        rows=[dict(r,text=noise(r['text'],kind)) for r in tests['frozen_v2']]
        noise_results[kind]=measure(rows,score(rows))
    samples=[]
    for _ in range(30):
        start=time.perf_counter();score([dict(text=ATTACKS[0])]);samples.append((time.perf_counter()-start)*1000)
    report=dict(metadata=metadata,checkpoint=str(checkpoint),head_sha256=sha(checkpoint/'head.pt'),
        encoder_hashes={str(p.relative_to(checkpoint/'encoder')):sha(p) for p in (checkpoint/'encoder').rglob('*') if p.is_file()},
        evaluation=evaluation,noise=noise_results,
        latency=dict(embedding_and_head_p50_ms=float(np.median(samples)),embedding_and_head_p95_ms=float(np.percentile(samples,95))),
        threshold=.65,calibrated=False,production_changed=False,
        limitations=['Bounded exploratory fine-tuning, not a completed hyperparameter search.',
            'Checkpoint chosen by validation loss. No test-based checkpoint selection.',
            'Scores are sigmoid outputs under synthetic training prevalence, not validated fraud probabilities.'])
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({name:r['metrics'] for name,r in evaluation.items()},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();run(args.checkpoint,args.output)
