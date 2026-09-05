"""Bounded, versioned model comparison; grouped selection; no production writes.

Run: python -m ml.hardening_experiments --output ml/artifacts/research/hardening-v2
All final evaluations are opened only after selection.json has been written.
"""
import argparse
import hashlib
import json
import platform
import resource
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC
from ml.hardening_data import DATA, ROOT, load, noise, NOISE_TYPES, load_frozen_v2
from ml.dataset import sha
from ml.embeddings import get_embedding_model, MODEL_NAME
from ml.classifier import V2_DIR
from ml.v2_experiments import metrics, probability, reliability

SEED = 42
SPECS = [dict(name=f'lr-c{c}-{w or "plain"}',kind='lr',C=c,class_weight=w)
         for c in (1.,10.,100.) for w in (None,'balanced')] + [
    dict(name='lr-sigmoid',kind='lr_sigmoid',C=10.,class_weight='balanced'),
    dict(name='svm-sigmoid',kind='svm_sigmoid',C=1.,class_weight='balanced'),
    dict(name='mlp-32',kind='mlp',hidden=32,alpha=1.),
    dict(name='mlp-64',kind='mlp',hidden=64,alpha=5.),
    dict(name='hist-boost',kind='hist_boost')]


def folds(y, groups, n=5):
    return list(StratifiedGroupKFold(n_splits=n,shuffle=True,random_state=SEED).split(np.zeros(len(y)),y,groups))


def estimator(spec,y,groups):
    kind=spec['kind']
    if kind=='mlp':
        # Scaling is fitted inside every group fold. No random internal validation split.
        return make_pipeline(StandardScaler(),MLPClassifier(hidden_layer_sizes=(spec['hidden'],),alpha=spec['alpha'],
            max_iter=250,batch_size=32,early_stopping=False,random_state=SEED))
    if kind=='hist_boost':
        # Bounded nonlinear control: tests whether interactions justify axis-aligned trees.
        return HistGradientBoostingClassifier(max_iter=80,max_leaf_nodes=7,min_samples_leaf=20,
            l2_regularization=10.,early_stopping=False,random_state=SEED)
    args=dict(C=spec['C'],class_weight=spec['class_weight'],random_state=SEED,max_iter=5000)
    base=LinearSVC(**args) if kind.startswith('svm') else LogisticRegression(**args)
    if kind.endswith('sigmoid'):
        return CalibratedClassifierCV(base,method='sigmoid',cv=folds(y,groups,3),ensemble=True)
    return base


def labels(rows):return np.asarray([r['label']=='scam' for r in rows],dtype=int)


def measure(rows,p):
    y=labels(rows)
    result=metrics(y,p);tn,fp=result['confusion_matrix'][0];fn,tp=result['confusion_matrix'][1]
    result.update(false_positive_rate=fp/(tn+fp) if tn+fp else None,false_negative_rate=fn/(fn+tp) if fn+tp else None)
    def subgroup(indices):
        return metrics(y[indices],p[indices]) if indices else None
    sub={}
    for field in ('language','category'):
        sub[field]={str(v):subgroup([i for i,r in enumerate(rows) if r.get(field)==v]) for v in sorted({r.get(field,'Unknown') for r in rows})}
    safety=[i for i,r in enumerate(rows) if r.get('safety_context') is True or r.get('category') in {'safety','educational','quoted_education','cybersecurity_education'}]
    implicit=[i for i,r in enumerate(rows) if r.get('implicit_request') is True or r.get('category') in {'implicit_sensitive','euphemistic','implicit','implicit_otp','contradiction'} and r['label']=='scam']
    return dict(metrics=result,reliability=reliability(y,p),subgroups=sub,
        safety_negatives=subgroup([i for i in safety if y[i]==0]),implicit_requests=subgroup(implicit),
        predictions=[dict(id=r.get('id',str(i)),score=float(p[i]),label=r['label']) for i,r in enumerate(rows)])


def selection_value(rows,p):
    clean=[i for i,r in enumerate(rows) if r.get('noise_type') is None]
    safe=[i for i in clean if rows[i].get('safety_context') is True]
    y=labels(rows); m=metrics(y[clean],p[clean]); sfpr=float(np.mean(p[safe]>=.65)) if safe else 0.
    return (m['f1']-.5*sfpr,-m['brier'])


def signal_models(X,rows,Xv,valid,output):
    from schemas.signals import SignalCode
    ix=[i for i,r in enumerate(rows) if r.get('signals') is not None]
    vi=[i for i,r in enumerate(valid) if r.get('signals') is not None]
    models={};report={}
    for code in SignalCode:
        y=np.asarray([code in rows[i]['signals'] for i in ix],dtype=int)
        vy=np.asarray([code in valid[i]['signals'] for i in vi],dtype=int)
        if min(np.bincount(y,minlength=2))<5:
            report[code]=dict(status='insufficient_support',train_positive=int(y.sum()));continue
        model=LogisticRegression(C=1.,class_weight='balanced',max_iter=3000,random_state=SEED).fit(X[ix],y)
        models[code]=model
        report[code]=dict(status='research_only',train_positive=int(y.sum()),validation=metrics(vy,probability(model,Xv[vi]),.8))
    joblib.dump(models,output/'signals.joblib')
    return dict(threshold=.8,models=report,integrated=False,
                policy='Require independent positive support and high precision for every integrated head; no automatic integration.')


def run(output):
    if output.exists():raise FileExistsError('Choose a new version directory')
    start=time.perf_counter();train,valid=load('train'),load('validation')
    if {r['group'] for r in train}&{r['group'] for r in valid}:raise ValueError('Group leakage')
    manifest_hash=sha(DATA/'manifest.json'); baseline_hash=sha(V2_DIR/'classifier.joblib')
    import torch
    torch.set_num_threads(4)
    encoder=get_embedding_model()
    def encode(rows):return np.asarray(encoder.encode([r['text'] for r in rows],normalize_embeddings=True,show_progress_bar=False))
    X,Xv=encode(train),encode(valid); embedding_seconds=time.perf_counter()-start
    y=labels(train);groups=[r['group'] for r in train];cv=folds(y,groups)
    output.mkdir(parents=True);models={};results={};scores={};fit_start=time.perf_counter()
    for spec in SPECS:
        t=time.perf_counter();oof=np.zeros(len(y));caught=[]
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter('always',ConvergenceWarning)
            for tr,va in cv:
                model=estimator(spec,y[tr],np.asarray(groups)[tr]);model.fit(X[tr],y[tr]);oof[va]=probability(model,X[va])
            model=estimator(spec,y,groups).fit(X,y)
            caught=[str(w.message) for w in ws if issubclass(w.category,ConvergenceWarning)]
        name=spec['name'];models[name]=model;scores[name]=selection_value(train,oof)
        path=output/(name+'.joblib');joblib.dump(model,path)
        results[name]=dict(spec=spec,training_seconds=time.perf_counter()-t,artifact_sha256=sha(path),
            oof=measure(train,oof),selection_value=scores[name],convergence_warnings=caught,
            validation=measure(valid,probability(model,Xv)))
        print(json.dumps(dict(candidate=name,seconds=round(results[name]['training_seconds'],2),oof_f1=results[name]['oof']['metrics']['f1'],validation_f1=results[name]['validation']['metrics']['f1'])),flush=True)
    selected=max(scores,key=scores.get)
    receipt=dict(model_version=output.name,selected_candidate=selected,dataset_version='hardening-v2',dataset_manifest_sha256=manifest_hash,
        dataset_hashes={s:sha(DATA/f'{s}.json') for s in ('train','validation','test')},embedding_model=MODEL_NAME,
        normalize_embeddings=True,seed=SEED,created_at=datetime.now(timezone.utc).isoformat(),train_samples=len(train),
        threshold_policy='Unchanged .65 moderate/.80 high; diagnostic scores, not fraud probabilities.',
        selection_policy='Grouped train-only OOF clean F1 minus 0.5*safety FPR at .65, then lower Brier. No final-test selection.',
        production_changed=False,production_sha256=baseline_hash,candidates=results,
        embedding_seconds=embedding_seconds,training_seconds=time.perf_counter()-fit_start,
        environment=dict(python=platform.python_version(),platform=platform.machine(),numpy=np.__version__,
            sklearn=__import__('sklearn').__version__,torch=torch.__version__,mps_available=torch.backends.mps.is_available()),
        excluded=dict(isotonic='Too few independent calibration groups; nonparametric calibration would be unstable.',
            transformer='Cached 465 MiB MiniLM; MPS unavailable in this process. Full encoder training estimated 3–5 GiB RAM, up to 1 GiB extra disk, tens of CPU minutes. Data lacks native review; no costly encoder run justified.'))
    (output/'selection.json').write_text(json.dumps(receipt,indent=2)+'\n')
    # Selection is now immutable. Open final evaluations only from this point.
    from tests.implicit_code_cases import ATTACKS,SAFE
    tests={'new_grouped_test':load('test'),'frozen_v2':load_frozen_v2(),
        'implicit_family':[dict(id=f'family-{i}',text=t,label='scam' if i<len(ATTACKS) else 'safe',language='Unknown',category='implicit' if i<len(ATTACKS) else 'safety',safety_context=i>=len(ATTACKS)) for i,t in enumerate(ATTACKS+SAFE)],
        'adversarial':json.loads((ROOT.parents[1]/'evaluation/hardening/adversarial_cases.json').read_text())}
    models['production-v2']=joblib.load(V2_DIR/'classifier.joblib')
    prior=ROOT.parents[1]/'evaluation/hardening/research-1/classifier.joblib'
    if prior.exists():models['research-1']=joblib.load(prior)
    evaluation={};noise_results={}
    for dataset,rows in tests.items():
        for r in rows:r.setdefault('language','Unknown');r.setdefault('category','Unknown')
        vectors=encode(rows)
        evaluation[dataset]={name:measure(rows,probability(model,vectors)) for name,model in models.items()}
    # Paired simulated noise is reported separately from clean, independent sample counts.
    for kind in NOISE_TYPES:
        rows=[dict(r,text=noise(r['text'],kind)) for r in tests['frozen_v2']]
        vectors=encode(rows)
        noise_results[kind]=dict(changed=sum(a['text']!=b['text'] for a,b in zip(rows,tests['frozen_v2'])),
            models={name:measure(rows,probability(model,vectors)) for name,model in models.items()})
    signals=signal_models(X,train,Xv,valid,output)
    latency={}
    for name,model in models.items():
        samples=[]
        for _ in range(50):
            t=time.perf_counter();probability(model,X[:1]);samples.append((time.perf_counter()-t)*1000)
        latency[name]=dict(classifier_p50_ms=float(np.median(samples)),classifier_p95_ms=float(np.percentile(samples,95)))
    samples=[]
    for _ in range(30):
        t=time.perf_counter();v=encode([dict(text=ATTACKS[0])]);probability(models[selected],v);samples.append((time.perf_counter()-t)*1000)
    latency[selected]['embedding_and_classifier_p50_ms']=float(np.median(samples))
    latency[selected]['embedding_and_classifier_p95_ms']=float(np.percentile(samples,95))
    # All signal heads get an untouched test evaluation, including zero-support heads.
    heads=joblib.load(output/'signals.joblib');rows=tests['new_grouped_test'];vectors=encode(rows)
    signals['test']={code:metrics([int(code in r['signals']) for r in rows],probability(model,vectors),.8) for code,model in heads.items()}
    baseline=evaluation['frozen_v2']['production-v2']['metrics'];candidate=evaluation['frozen_v2'][selected]['metrics']
    report=dict(selected_candidate=selected,evaluation=evaluation,noise=noise_results,signals=signals,latency=latency,
        elapsed_seconds=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        acceptance=dict(production_changed=False,baseline_frozen_f1=baseline['f1'],candidate_frozen_f1=candidate['f1'],
            reason='No automatic promotion. Native-reviewed field acceptance data absent; review paired language/safety metrics and existing regressions before any deployment.'),
        limitations=['New test is synthetic, not field validation. Frozen v2 test is historically inspected.',
            'Related translations and noise share groups. Four lower-similarity leakage candidates remain review flags; see dataset manifest.',
            'Sigmoid uses grouped inner calibration folds; artificial prevalence does not establish real-world scam probabilities.',
            'Noise is simulated text corruption, not labelled OCR or speech recordings.'])
    assert sha(DATA/'manifest.json')==manifest_hash and sha(V2_DIR/'classifier.joblib')==baseline_hash
    (output/'benchmark.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(selected=selected,frozen={n:r['metrics'] for n,r in evaluation['frozen_v2'].items()},new_test={n:r['metrics'] for n,r in evaluation['new_grouped_test'].items()}),indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
