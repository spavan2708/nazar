"""Reproducible V12 training and frozen held-out evaluation.
Train: python -m ml.train_v2 [--output ml/artifacts/v2]
Evaluate saved model only: python -m ml.train_v2 --evaluate-only
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import hashlib

import joblib
import numpy as np
from sentence_transformers import SentenceTransformer

from ml.classifier import CLASSIFIER_PATH, EMBEDDING_MODEL_PATH, METADATA_PATH
from ml.v2_data import DATA, digest, load_frozen
from ml.v2_experiments import SEED, metrics, probability, reliability, select
from services.text_analyzer import analyze_text

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / 'ml/artifacts/v2'
REPORT = ROOT / 'evaluation/V12_ML_BENCHMARK.md'


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def embeddings(model, rows):
    return model.encode([r['text'] for r in rows], normalize_embeddings=True, show_progress_bar=False)


def breakdown(rows):
    return {key:dict(Counter(row[key] for row in rows)) for key in ('label','language','category')}


def evaluate(model, embedding, rows):
    X = embeddings(embedding, rows)
    y = np.array([int(r['label']=='scam') for r in rows])
    old = joblib.load(CLASSIFIER_PATH)
    probabilities = {'v1': probability(old,X), 'v2':probability(model,X),
        'V3': np.array([analyze_text(r['text']).score / 100 for r in rows])}
    output = {}
    for name,p in probabilities.items():
        groups = {}
        selectors = {language:[i for i,r in enumerate(rows) if r['language']==language] for language in sorted({r['language'] for r in rows})}
        selectors['Hinglish/Tanglish'] = [i for i,r in enumerate(rows) if r['language'] in ('Hinglish','Tanglish')]
        for cat in ('safety','hard_negative','implicit_sensitive'):
            selectors[cat] = [i for i,r in enumerate(rows) if r['category']==cat]
        for group, indices in selectors.items():
            if indices: groups[group] = metrics(y[indices],p[indices])
        wrong_positive = [i for i in range(len(y)) if not y[i] and p[i]>=.65]
        wrong_negative = [i for i in range(len(y)) if y[i] and p[i]<.65]
        def details(indices):
            return [dict(id=rows[i]['id'], text=rows[i]['text'], language=rows[i]['language'],category=rows[i]['category'], label=rows[i]['label'], value=float(p[i])) for i in indices]
        output[name] = dict(metrics=metrics(y,p), subgroups=groups,
            thresholds=[metrics(y,p,t) for t in (.50,.55,.60,.65,.70,.75)],
            calibration=reliability(y,p) if name!='V3' else None,
            false_positives=details(wrong_positive),false_negatives=details(wrong_negative),
            lowest_scams=details(sorted(np.where(y==1)[0],key=lambda i:p[i])[:10]),
            highest_benign=details(sorted(np.where(y==0)[0],key=lambda i:-p[i])[:10]),
            predictions=details(range(len(rows))))
        if name == 'V3':
            output[name]['reference_operating_points'] = {
                'any_nonzero_signal_score':metrics(y,p,.01),
                'medium_or_higher':metrics(y,p,.30),
                'high_or_higher':metrics(y,p,.65)}
    return output


def report(metadata, results, path):
    lines = ['# V12 ML benchmark', '',
        'Synthetic prototype challenge; these results are not production accuracy or real-world scam probabilities.', '',
        '## Dataset and leakage controls', '',
        f'Train: {metadata["counts"]["train"]}; held-out evaluation: {metadata["counts"]["eval"]}. Both splits are balanced.',
        'Examples are fixed, manually authored synthetic scenarios with language/category/difficulty/source metadata. Training and evaluation files were frozen before model selection. Evaluation is checked against v2 training and all 48 original v1 examples for normalized exact and ≥0.90 character-similarity overlap.',
        'Related multilingual training variants share groups; outer and inner calibration folds keep groups together. Five-fold grouped cross-validation uses training only. Semantic/topic overlap across splits cannot be ruled out; translations are not independent real-world observations.', '',
        '```json', json.dumps(metadata['breakdown'],ensure_ascii=False,indent=2), '```', '',
        'Dataset SHA-256 hashes: `' + json.dumps(metadata['dataset_hashes']) + '`', '',
        '## Original model and experiment selection', '',
        'v1: existing LogisticRegression(C=1, class_weight=balanced), fitted on 36 of 48 prototype records with the same multilingual MiniLM embeddings. Its preserved classifier hash is recorded in metadata.',
        'v2 uses the existing local sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 embeddings. No embedding retraining or download was performed.',
        'Selection was fixed before held-out evaluation: highest training out-of-fold F1 at 0.65, then lowest Brier score, then average precision. Candidate C/class-weight choices below were not tuned on held-out results.',
        'Selected: `' + json.dumps(metadata['selected']) + '`.', '',
        '| Candidate | C | Class weight | OOF F1 @ .65 | Brier | ECE | PR-AUC (AP) |', '|---|---:|---|---:|---:|---:|---:|']
    for row in metadata['cv_results']:
        s,m=row['spec'],row['metrics']
        lines.append(f"| {s['kind']} | {s['C']} | {s['class_weight']} | {m['f1']:.3f} | {m['brier']:.3f} | {row['calibration']['ece']:.3f} | {m['pr_auc']:.3f} |")
    lines += ['', 'Sigmoid calibration is nested within each outer training fold. Isotonic was not included: 150 training rows and small grouped calibration folds are insufficient to support a flexible nonparametric calibration fit.', '',
        '## Held-out results', '',
        'All three systems use the same 90 records. Classification metrics use 0.65 for v1/v2; the V3 reference uses score ≥65 (the existing high-risk boundary). V3 scores are severity values, not calibrated probabilities. PR-AUC below is average precision; V3 Brier/log-loss values in machine-readable output are not calibration claims.', '',
        '| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC (AP) | Confusion [[TN,FP],[FN,TP]] |', '|---|---:|---:|---:|---:|---:|---:|---|']
    for name,r in results.items():
        m=r['metrics'];lines.append(f"| {name} | {m['accuracy']:.3f} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {m['roc_auc']:.3f} | {m['pr_auc']:.3f} | {m['confusion_matrix']} |")
    lines += ['', 'V3 secondary reference points (not probability thresholds):', '', '| Decision | Precision | Recall | F1 | Confusion |', '|---|---:|---:|---:|---|']
    for label,m in results['V3']['reference_operating_points'].items():
        lines.append(f"| {label} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {m['confusion_matrix']} |")
    lines += ['', 'The V3 high-risk reference misses every scam in this deliberately paraphrastic/multilingual holdout. The secondary table distinguishes this from no detection at all. These outcomes are retained without changing V3 or tuning this dataset after evaluation.']
    lines += ['', '## Subgroups at .65', '', 'Single-class groups have undefined ROC/PR-AUC. Precision/recall/F1 use zero when no positive prediction/label exists; FP/FN counts make safety-only groups interpretable.', '', '| Model | Subgroup | n | Precision | Recall | F1 | FP | FN |', '|---|---|---:|---:|---:|---:|---:|---:|']
    for name,r in results.items():
        for group,m in r['subgroups'].items():
            lines.append(f"| {name} | {group} | {m['n']} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {m['fp']} | {m['fn']} |")
    lines += ['', '## Threshold tradeoffs', '', '| Model | Threshold | Precision | Recall | FP | FN |', '|---|---:|---:|---:|---:|---:|']
    for name in ('v1','v2'):
        for m in results[name]['thresholds']:
            lines.append(f"| {name} | {m['threshold']:.2f} | {m['precision']:.3f} | {m['recall']:.3f} | {m['fp']} | {m['fn']} |")
    lines += ['', 'Lower thresholds generally catch more scams but can warn on legitimate messages. No production threshold change is applied or recommended from this small synthetic set alone. Retain 0.65 moderate and 0.80 high; collect independently labeled operational data before reviewing these boundaries.', '', '## Calibration', '']
    for name in ('v1','v2'):
        r=results[name];lines += [f"{name}: Brier {r['metrics']['brier']:.4f}; log loss {r['metrics']['log_loss']:.4f}; five-bin ECE {r['calibration']['ece']:.4f}.", '', '```json',json.dumps(r['calibration']['bins'],indent=2),'```','']
    lines += ['Calibration measured on an artificial 50/50 class balance does not establish calibration at real scam prevalence. Small bins and correlated examples limit reliability conclusions.', '', '## Error analysis', '']
    for name,r in results.items():
        lines += [f'### {name}', '']
        for key in ('false_positives','false_negatives','lowest_scams','highest_benign'):
            lines += [key.replace('_',' ').capitalize()+':', '']
            lines += [f"- {x['id']} ({x['language']}, {x['category']}, {x['value']:.4f}): {x['text']}" for x in r[key]] or ['- None.']
            lines.append('')
    lines += ['## Limitations and next steps', '',
        'Data is small, synthetic, authored by one process, and contains related translated scenarios. Scam labels encode the intended synthetic situation, not externally verified fraud. Native-speaker review and real consented/appropriately licensed data are needed. Grouped CV reduces but cannot eliminate semantic dependence. Local OCR/STT corruption here is simulated text, not an end-to-end media benchmark.',
        'Use a larger independently collected time-separated benchmark, more subtle safe support interactions, multilingual native-speaker labels and campaign-level grouping. Measure false-warning costs and calibration at realistic prevalence before deployment claims. Do not iteratively optimize against this frozen holdout; retire it as a development set if used to guide subsequent changes.',
        'No V5 calls were made. V3/V5, fusion thresholds, campaign scoring, OCR/STT and frontend behavior are unchanged.', '',
        '## Reproduction', '',
        'From backend, train to a fresh directory (existing artifacts are never overwritten):', '',
        '```bash', 'HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m ml.train_v2 --output ml/artifacts/v2-reproduction',
        'HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m ml.train_v2 --evaluate-only',
        '.venv/bin/python -m unittest discover -s tests -v', '```', '',
        'The default training output is ml/artifacts/v2. Runtime automatically selects v2 when present; NAZAR_ML_VERSION=v1 pins the preserved baseline and NAZAR_ML_VERSION=v2 requires v2. Missing/corrupt requested artifacts gracefully disable ML. Restart the backend to clear its cached model.',
        'Metadata records seed, data/model hashes, versions, selection receipt and held-out metrics. JSON report contains all predictions and error lists. Binary classifiers remain local and git-ignored; the existing embedding model is reused.']
    path.write_text('\n'.join(lines)+'\n')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=DEFAULT_OUTPUT);parser.add_argument('--evaluate-only',action='store_true');args=parser.parse_args()
    train, evaluation, hashes = load_frozen()
    if not EMBEDDING_MODEL_PATH.exists() or not CLASSIFIER_PATH.exists():
        raise RuntimeError('Existing local v1 classifier and multilingual embedding model are required; no automatic download.')
    output=args.output
    if not args.evaluate_only and output.exists():
        raise FileExistsError('Use a fresh --output directory; existing artifacts will not be overwritten.')
    embedding=SentenceTransformer(str(EMBEDDING_MODEL_PATH),local_files_only=True)
    if args.evaluate_only:
        metadata=json.loads((output/'metadata.json').read_text())
        if metadata['dataset_hashes'] != hashes or metadata['classifier_sha256'] != digest(output/'classifier.joblib') or metadata['v1_classifier_sha256'] != digest(CLASSIFIER_PATH):
            raise ValueError('Artifact or dataset fingerprint mismatch')
        model=joblib.load(output/'classifier.joblib')
    else:
        X=embeddings(embedding,train);y=np.array([int(r['label']=='scam') for r in train]);groups=np.array([r['group'] for r in train])
        model,winner,cv_results=select(X,y,groups)
        output.mkdir(parents=True)
        joblib.dump(model,output/'classifier.joblib')
        metadata=dict(model_version='v2',timestamp=datetime.now(timezone.utc).isoformat(),seed=SEED,
            embedding_model='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
            embedding_dimension=int(X.shape[1]), training_embeddings_sha256=hashlib.sha256(X.tobytes()).hexdigest(),
            classifier_sha256=digest(output/'classifier.joblib'), v1_classifier_sha256=digest(CLASSIFIER_PATH),
            v1_metadata=json.loads(METADATA_PATH.read_text()), dataset_hashes=hashes,
            counts=dict(train=len(train),eval=len(evaluation)), breakdown=dict(train=breakdown(train),eval=breakdown(evaluation)),
            packages={name:importlib.metadata.version(name) for name in ('numpy','scikit-learn','sentence-transformers','torch','joblib')},
            selected=winner['spec'],cv_results=cv_results,selection_policy='training grouped OOF F1 at .65, then Brier, then AP')
        # Written before the first held-out model prediction; selection cannot depend on it.
        save_json(output/'selection.json',metadata)
    results=evaluate(model,embedding,evaluation)
    metadata['evaluation_metrics']={name:value['metrics'] for name,value in results.items()}
    save_json(output/'metadata.json',metadata)
    save_json(output/'benchmark.json',results)
    # Keep a reviewable aggregate/full-prediction report outside ignored artifacts.
    report_path=REPORT if output.resolve()==DEFAULT_OUTPUT.resolve() else output/'V12_ML_BENCHMARK.md'
    report(metadata,results,report_path)
    if output.resolve()==DEFAULT_OUTPUT.resolve():
        save_json(ROOT/'evaluation/v12_results.json',dict(metadata=metadata,results=results))
    print(json.dumps(dict(selected=metadata['selected'],metrics=metadata['evaluation_metrics'],report=str(report_path)),indent=2))


if __name__=='__main__':
    main()
