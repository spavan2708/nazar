"""Post-selection evaluation of local recovery checkpoints and an offline hybrid.

No detector rules, language routing or model deployment are changed by this tool.
"""
import json,argparse,time,gc,unicodedata
from pathlib import Path
from collections import Counter
import numpy as np
import joblib
import torch
from sentence_transformers import SentenceTransformer
from ml.recovery import BASE,DATA,recovery_split,objective,language
from ml.hardening_data import load,load_frozen_v2,noise,NOISE_TYPES
from ml.hardening_experiments import measure
from ml.embeddings import get_embedding_model
from ml.classifier import V2_DIR
from ml.dataset import sha


def datasets():
    from tests.implicit_code_cases import ATTACKS,SAFE
    from services.language_detection import identify_language
    test=load_frozen_v2()
    result={'validation':recovery_split('validation'),'frozen90':test,'grouped85':load('test'),
        'family':[dict(id=f'family-{i}',text=t,label='scam' if i<len(ATTACKS) else 'safe',language=identify_language(t).detected_language,
            category='implicit' if i<len(ATTACKS) else 'safety',safety_context=i>=len(ATTACKS)) for i,t in enumerate(ATTACKS+SAFE)],
        'adversarial':json.loads((Path(__file__).parent/'hardening/adversarial_cases.json').read_text())}
    for kind in NOISE_TYPES:result['noise-'+kind]=[dict(r,text=noise(r['text'],kind)) for r in test]
    for rows in result.values():
        for r in rows:r.setdefault('language','Unknown');r.setdefault('category','Unknown')
    return result


def reliable_tamil(text):
    letters=[c for c in text if c.isalpha()]
    tamil=sum('TAMIL' in unicodedata.name(c,'') for c in letters)
    return tamil>=12 and tamil/max(1,len(letters))>=.9


def hybrid(rows,p,baseline):
    # Offline hypothesis: script evidence AND high-confidence source disagreement.
    # No routing for low-confidence Latin transliterations. Never installed in API.
    return np.array([b if reliable_tamil(r['text']) and b>=.8 and a<.65 else a for r,a,b in zip(rows,p,baseline)])


def qualify(name,scores,rows):
    p=scores[name];base=scores['hardening-encoder'];checks={}
    a=objective(rows['frozen90'],p['frozen90']);b=objective(rows['frozen90'],base['frozen90'])
    checks['overall_f1']=a['overall']['f1']>=b['overall']['f1']
    floors={'English':.8,'Hindi':.8,'Tamil':.8,'Hinglish':.8,'Tanglish':.8,'Mixed':.8}
    for lang,floor in floors.items():checks[lang+'_recall']=a['per_language'][lang]['recall']>=floor
    checks['frozen_safety']=a['safety_fpr']<=b['safety_fpr']
    af=objective(rows['family'],p['family']);bf=objective(rows['family'],base['family'])
    checks['implicit_family']=af['implicit_recall']>=bf['implicit_recall']
    checks['family_safety']=af['safety_fpr']<=bf['safety_fpr']
    checks['original_pair']=bool(p['family'][0]>=.8 and p['family'][23]<.65)
    checks['adversarial']=objective(rows['adversarial'],p['adversarial'])['overall']['f1']>=objective(rows['adversarial'],base['adversarial'])['overall']['f1']
    checks['grouped_test']=objective(rows['grouped85'],p['grouped85'])['overall']['f1']>=objective(rows['grouped85'],base['grouped85'])['overall']['f1']-.02
    return dict(checks=checks,passes_measured_guards=all(checks.values()),production_changed=False,
        limitation='Historically inspected, small synthetic tests cannot establish field reliability; no automatic promotion.')


def run(output):
    if output.exists():raise FileExistsError('Fresh report path required')
    torch.set_num_threads(4);rows=datasets();scores={};metadata={};latency={}
    paths={'hardening-encoder':BASE,**{k:BASE.parent/('recovery-'+k) for k in ('uniform','class','language_cluster')}}
    for name,path in paths.items():
        metadata[name]=json.loads((path/'metadata.json').read_text())
        model=SentenceTransformer(str(path/'encoder'),local_files_only=True,device='cpu');head=torch.nn.Linear(model.get_sentence_embedding_dimension(),1)
        head.load_state_dict(torch.load(path/'head.pt',weights_only=True,map_location='cpu'));model.eval();head.eval()
        def predict(rs):
            with torch.no_grad():return torch.sigmoid(head(model.encode([r['text'] for r in rs],convert_to_tensor=True,show_progress_bar=False)).squeeze(-1)).numpy()
        scores[name]={k:predict(rs) for k,rs in rows.items()};samples=[]
        for _ in range(20):
            t=time.perf_counter();predict(rows['family'][:1]);samples.append((time.perf_counter()-t)*1000)
        latency[name]=dict(p50_ms=float(np.median(samples)),p95_ms=float(np.percentile(samples,95)))
        metadata[name]['head_sha256']=sha(path/'head.pt')
        del model,head;gc.collect()
    encoder=get_embedding_model();classifier=joblib.load(V2_DIR/'classifier.joblib')
    scores['production-v2']={k:classifier.predict_proba(encoder.encode([r['text'] for r in rs],normalize_embeddings=True))[:,list(classifier.classes_).index(1)] for k,rs in rows.items()}
    # Pick recovery source with validation objective only, never final benchmarks.
    winner=max(('uniform','class','language_cluster'),key=lambda n:objective(rows['validation'],scores[n]['validation'])['objective'])
    scores['offline-hybrid']={k:hybrid(rs,scores[winner][k],scores['production-v2'][k]) for k,rs in rows.items()}
    report=dict(metadata=metadata,latency=latency,hybrid_source=winner,hybrid_policy='Tamil script >=90% and >=12 letters, production >=.80, encoder <.65; otherwise encoder. Offline only.',
        dataset_hash=sha(DATA/'manifest.json'),production_hash=sha(V2_DIR/'classifier.joblib'),threshold=.65,
        results={name:{k:dict(multilingual=objective(rows[k],p),detail=measure(rows[k],p)) for k,p in ds.items()} for name,ds in scores.items()},
        acceptance={name:qualify(name,scores,rows) for name in scores if name not in ('production-v2','hardening-encoder')},
        original_pair={name:dict(attack=float(ds['family'][0]),safe=float(ds['family'][23])) for name,ds in scores.items()},
        limitations=['Synthetic authored/adapted data, not native validated.','Some language slices have only five positive examples.',
            'No production changes or runtime routing. Scores are uncalibrated evidence.','Simulated OCR/STT noise is not real transcription accuracy.'])
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(acceptance=report['acceptance'],pairs=report['original_pair']),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
