"""Offline research; selection uses grouped training folds and never promotes models."""
import argparse,json,platform,resource,time
from datetime import datetime,timezone
from pathlib import Path
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from ml.dataset import DATA,load_split,assert_training_separation,quality,sha
from ml.embeddings import get_embedding_model,MODEL_NAME
from ml.noise import variants
from ml.v2_experiments import select,probability,metrics,reliability
from ml.classifier import CLASSIFIER_PATH,V2_DIR

def measurement(rows,p):
    y=np.array([r['label']=='scam' for r in rows],dtype=int);m=metrics(y,p)
    tn,fp=m['confusion_matrix'][0];fn,tp=m['confusion_matrix'][1]
    m.update(false_positive_rate=fp/(fp+tn) if fp+tn else None,false_negative_rate=fn/(fn+tp) if fn+tp else None)
    groups={}
    for field in ('language','category'):
        groups[field]={}
        for value in sorted({r[field] for r in rows}):
            ix=[i for i,r in enumerate(rows) if r[field]==value];groups[field][value]=metrics(y[ix],p[ix])
    ix=[i for i,r in enumerate(rows) if r['label']=='safe']
    return dict(metrics=m,calibration=reliability(y,p),subgroups=groups,
        benign_controls=metrics(y[ix],p[ix]) if ix else None,
        thresholds=[metrics(y,p,t) for t in (.5,.55,.6,.65,.7,.75,.8)],
        predictions=[dict(id=r['id'],label=r['label'],score=float(v)) for r,v in zip(rows,p)])

def signal_research(X,rows,Xv,validation):
    from schemas.signals import SignalCode
    ix=[i for i,r in enumerate(rows) if r.get('signals') is not None]
    vi=[i for i,r in enumerate(validation) if r.get('signals') is not None]
    result={};models={}
    for code in SignalCode:
        y=np.array([code in rows[i]['signals'] for i in ix],dtype=int)
        vy=np.array([code in validation[i]['signals'] for i in vi],dtype=int)
        if min(np.bincount(y,minlength=2))<5:
            result[code]=dict(status='insufficient_training_support',positive_count=int(y.sum()));continue
        model=LogisticRegression(C=1,class_weight='balanced',random_state=42,max_iter=2000).fit(X[ix],y)
        result[code]=dict(status='research_only',validation=metrics(vy,probability(model,Xv[vi]),.8),threshold=.8,training_positives=int(y.sum()))
        models[code]=model
    return models,dict(signals=result,validation_annotated=len(vi),integrated=False,reason='Too few independent annotated examples for production integration.')

def run(output):
    if output.exists():raise FileExistsError('Use a fresh run directory')
    train,valid=load_split('train'),load_split('validation');assert_training_separation(train,valid)
    start=time.perf_counter();embedding=get_embedding_model()
    X=np.asarray(embedding.encode([r['text'] for r in train],normalize_embeddings=True))
    Xv=np.asarray(embedding.encode([r['text'] for r in valid],normalize_embeddings=True))
    embedding_seconds=time.perf_counter()-start;start=time.perf_counter()
    candidate,winner,cv=select(X,[int(r['label']=='scam') for r in train],[r['group'] for r in train])
    output.mkdir(parents=True);joblib.dump(candidate,output/'classifier.joblib')
    receipt=dict(model_version=output.name,architecture=winner['spec'],embedding_model=MODEL_NAME,
        dataset_manifest_sha256=sha(DATA/'manifest.json'),seed=42,created_at=datetime.now(timezone.utc).isoformat(),
        selection='train-only grouped OOF F1 at .65, then Brier and AP',cv_results=cv,
        classifier_sha256=sha(output/'classifier.joblib'),threshold_policy='unchanged .65/.80; no automatic promotion',
        resources=dict(embedding_seconds=embedding_seconds,training_seconds=time.perf_counter()-start,python=platform.python_version()))
    (output/'selection.json').write_text(json.dumps(receipt,indent=2)+'\n')
    models={'v1':joblib.load(CLASSIFIER_PATH),'v2':joblib.load(V2_DIR/'classifier.joblib'),'candidate':candidate}
    validation={name:measurement(valid,probability(model,Xv)) for name,model in models.items()}
    signals,signal_result=signal_research(X,train,Xv,valid);joblib.dump(signals,output/'signals.joblib')
    test=load_split('test');Xt=np.asarray(embedding.encode([r['text'] for r in test],normalize_embeddings=True))
    tests={name:measurement(test,probability(model,Xt)) for name,model in models.items()};noise={}
    for kind in variants('probe'):
        N=np.asarray(embedding.encode([variants(r['text'],42+i)[kind] for i,r in enumerate(test)],normalize_embeddings=True))
        noise[kind]={name:measurement(test,probability(model,N)) for name,model in models.items()}
    audit=quality({'train':train,'validation':valid,'test':test},np.vstack([X,Xv,Xt]));latency={}
    for name,model in models.items():
        samples=[]
        for _ in range(30):
            t=time.perf_counter();probability(model,Xt[:1]);samples.append((time.perf_counter()-t)*1000)
        latency[name]={'classifier_only_p50_ms':float(np.median(samples)),'classifier_only_p95_ms':float(np.percentile(samples,95))}
    report=dict(metadata=receipt,validation=validation,test=tests,noise=noise,quality=audit,signals=signal_result,latency=latency,
        peak_rss_platform_units=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        production=dict(model='v2',thresholds=[.65,.8],changed=False,reason='Independent acceptance data and semantic-overlap review required; no automatic promotion.'),
        rejected_architectures={'isotonic':'Too few independent calibration groups','MLP':'260 synthetic development rows do not justify higher capacity','gradient_boosting':'No evidence axis-aligned embedding splits justify complexity'},
        cost_policy='False negatives risk missed scams; false positives cause warning fatigue. Threshold sweeps are descriptive only.',
        limitations=['Synthetic labels, no native review','Noise probes are paired simulated text','PR-AUC is average precision','Artificial prevalence does not establish fraud probabilities'])
    (output/'benchmark.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(output),'test':{k:v['metrics'] for k,v in tests.items()},'quality_conflicts':len(audit['blocking_cross_split_overlaps']),'semantic_review_candidates':len(audit['semantic_review_candidates'])},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
