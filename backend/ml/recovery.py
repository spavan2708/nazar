"""Targeted multilingual recovery. Build and train are explicit, research-only commands."""
import argparse,csv,json,hashlib,time,random
from pathlib import Path
from collections import Counter,defaultdict
from difflib import SequenceMatcher
import numpy as np
from ml.hardening_data import ResearchExample,load,load_frozen_v2,normalized
from ml.dataset import sha
from ml.embeddings import get_embedding_model

DATA=Path(__file__).parent/'data/recovery_v1'
BASE=Path(__file__).parent/'artifacts/research/hardening-v2-encoder'


def language(row):
    value=row.get('language','Unknown')
    return 'Mixed' if value.startswith('Mixed') else value


def objective(rows,p):
    from ml.v2_experiments import metrics
    y=np.array([r['label']=='scam' for r in rows],int)
    overall=metrics(y,p); per={}
    for lang in sorted({language(r) for r in rows}):
        ix=[i for i,r in enumerate(rows) if language(r)==lang];per[lang]=metrics(y[ix],p[ix])
    supported=[v for v in per.values() if sum(v['confusion_matrix'][1])>0]
    safe=[i for i,r in enumerate(rows) if r.get('safety_context') or r.get('category') in {'safety','educational','quoted_education'}]
    safe=[i for i in safe if not y[i]]
    implicit=[i for i,r in enumerate(rows) if y[i] and (r.get('implicit_request') or r.get('category') in {'implicit_sensitive','implicit','euphemistic','contradiction'})]
    sfpr=float(np.mean(p[safe]>=.65)) if safe else None
    ir=float(np.mean(p[implicit]>=.65)) if implicit else None
    macro=float(np.mean([v['f1'] for v in supported])) if supported else 0.
    worst=min((v['recall'] for v in supported),default=0.)
    return dict(overall=overall,per_language=per,macro_f1=macro,macro_precision=float(np.mean([v['precision'] for v in supported])),
        macro_recall=float(np.mean([v['recall'] for v in supported])),worst_recall=worst,safety_fpr=sfpr,implicit_recall=ir,
        objective=.35*overall['f1']+.35*macro+.15*worst+.15*(ir or 0)-.5*(sfpr or 0),
        unsupported_positive_languages=[k for k,v in per.items() if not sum(v['confusion_matrix'][1])])


def build():
    if (DATA/'manifest.json').exists():raise FileExistsError('Recovery version already frozen')
    rows=[]
    for i,r in enumerate(csv.DictReader((DATA/'pairs.tsv').open(),delimiter='\t')):
        for label in ('scam','safe'):
            g=r['group'].strip()
            rows.append(ResearchExample(id=f'recovery-{i+1:03}-{label}',text=r[label],label=label,language=r['language'],language_style=r['language'],
                category=r['category'] if label=='scam' else ('quoted_education' if r['category']=='quoted_education' else 'safety'),
                difficulty='hard',source_type='synthetic_authored' if r['language']=='Tamil' else 'synthetic_translated',group=g,cluster_id=g,
                signals=r['signals'].split(',') if label=='scam' else [],safety_context=label=='safe',implicit_request=label=='scam' and r['implicit']=='true',
                notes='AI-authored conversational Tamil / adapted Tanglish; no native-speaker validation. Matched pairs and adaptations share groups.').model_dump(mode='json'))
    train,valid=load('train'),load('validation')
    from tests.implicit_code_cases import ATTACKS,SAFE
    protected=valid+load('test')+load_frozen_v2()+[dict(id=f'family-{i}',text=t) for i,t in enumerate(ATTACKS+SAFE)]
    protected+=json.loads((Path(__file__).parents[1]/'evaluation/hardening/adversarial_cases.json').read_text())
    encoder=get_embedding_model();X=np.asarray(encoder.encode([r['text'] for r in rows],normalize_embeddings=True));Z=np.asarray(encoder.encode([r['text'] for r in protected],normalize_embeddings=True))
    sims=X@Z.T; blocked=set();overlap=[];review=[]
    for i,r in enumerate(rows):
        for j,p in enumerate(protected):
            exact=normalized(r['text'])==normalized(p['text'])
            near=SequenceMatcher(None,normalized(r['text']),normalized(p['text']),autojunk=False).ratio()>=.90
            if exact or near or sims[i,j]>=.95:
                blocked.add(r['group']);overlap.append(dict(id=r['id'],protected=p['id'],exact=exact,near=near,cosine=float(sims[i,j])))
            elif sims[i,j]>=.90:review.append(dict(id=r['id'],protected=p['id'],cosine=float(sims[i,j])))
    # New families resembling existing training stay with that training family.
    T=np.asarray(encoder.encode([r['text'] for r in train],normalize_embeddings=True));links={}
    for i,r in enumerate(rows):
        j=int(np.argmax(X[i]@T.T))
        if float(X[i]@T[j])>=.95:links[r['group']]=train[j]['group']
    kept=[];seen={normalized(r['text']) for r in train};duplicate=[]
    for r in rows:
        if r['group'] in blocked:continue
        key=normalized(r['text'])
        if key in seen:duplicate.append(r['id']);continue
        seen.add(key)
        group=links.get(r['group'],r['group'])
        split='train' if r['group'] in links or int(hashlib.sha256(group.encode()).hexdigest()[:8],16)%4 else 'validation'
        row=dict(r,group=group,cluster_id=group);(train if split=='train' else valid).append(row);kept.append(dict(id=r['id'],split=split))
    assert not ({r['group'] for r in train}&{r['group'] for r in valid})
    for name,records in [('train',train),('validation',valid)]:
        (DATA/f'{name}.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    manifest=dict(version='recovery-v1',source_hash=sha(DATA/'pairs.tsv'),base_manifest_sha256=sha(Path(__file__).parent/'data/hardening_v2/manifest.json'),
        splits={s:sha(DATA/f'{s}.json') for s in ('train','validation')},draft_rows=len(rows),kept=kept,quarantined_groups=sorted(blocked),overlap=overlap,semantic_review=review,duplicates=duplicate,
        provenance='Synthetic/adapted; no native review. No changes to frozen test or existing grouped test.',
        counts={s:dict(n=len(rs),language=dict(Counter(r['language'] for r in rs)),label=dict(Counter(r['label'] for r in rs))) for s,rs in [('train',train),('validation',valid)]})
    (DATA/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(kept=len(kept),quarantined=len(rows)-len(kept)-len(duplicate),counts=manifest['counts']),indent=2))


def recovery_split(split):
    manifest=json.loads((DATA/'manifest.json').read_text());p=DATA/f'{split}.json'
    if sha(p)!=manifest['splits'][split]:raise ValueError('Recovery fingerprint mismatch')
    return json.loads(p.read_text())


def sampling_weights(rows,kind):
    if kind=='uniform':return np.ones(len(rows))
    if kind=='class':
        counts=Counter(r['label'] for r in rows);return np.array([1/counts[r['label']] for r in rows])
    buckets=defaultdict(set);counts=Counter((language(r),r['label'],r['group']) for r in rows)
    for lang,label,group in counts:buckets[lang,label].add(group)
    w=np.array([1/(len(buckets[language(r),r['label']])*counts[language(r),r['label'],r['group']]) for r in rows])
    return np.minimum(w/w.mean(),4.)


def train_run(output,kind):
    if output.exists():raise FileExistsError('Use a new model version')
    import torch
    from sentence_transformers import SentenceTransformer
    from ml.finetune import to_device
    torch.set_num_threads(4);torch.manual_seed(42);random.seed(42)
    train,valid=recovery_split('train'),recovery_split('validation')
    model=SentenceTransformer(str(BASE/'encoder'),local_files_only=True,device='cpu')
    head=torch.nn.Linear(model.get_sentence_embedding_dimension(),1)
    head.load_state_dict(torch.load(BASE/'head.pt',weights_only=True,map_location='cpu'))
    optimizer=torch.optim.AdamW(list(model.parameters())+list(head.parameters()),lr=5e-6)
    def evaluate():
        model.eval();head.eval()
        with torch.no_grad():p=torch.sigmoid(head(model.encode([r['text'] for r in valid],convert_to_tensor=True,show_progress_bar=False)).squeeze(-1)).numpy()
        return objective(valid,p)
    base=evaluate();best=base['objective'];best_epoch=0;history=[];steps=0;start=time.perf_counter();output.mkdir(parents=True)
    model.save(str(output/'encoder'));torch.save(head.state_dict(),output/'head.pt')
    weights=sampling_weights(train,kind)
    for epoch in range(2):
        model.train();head.train()
        if kind=='uniform':order=list(range(len(train)));random.Random(42+epoch).shuffle(order)
        else:order=list(torch.utils.data.WeightedRandomSampler(weights,len(train),replacement=True,generator=torch.Generator().manual_seed(42+epoch)))
        for i in range(0,len(order),4):
            if time.perf_counter()-start>120:break
            rows=[train[j] for j in order[i:i+4]];features=to_device(model.tokenize([r['text'] for r in rows]),'cpu')
            logits=head(model(features)['sentence_embedding']).squeeze(-1);y=torch.tensor([r['label']=='scam' for r in rows],dtype=torch.float32)
            loss=torch.nn.functional.binary_cross_entropy_with_logits(logits,y);optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(list(model.parameters())+list(head.parameters()),1.);optimizer.step();steps+=1
        result=evaluate();history.append(dict(epoch=epoch+1,validation=result,steps=steps))
        guard=(result['safety_fpr']<=(base['safety_fpr'] or 0)+.05 and result['implicit_recall']>=(base['implicit_recall'] or 0)-.05
            and all(result['per_language'][l]['recall']>=base['per_language'][l]['recall']-.10 for l in ('English','Hinglish')))
        if guard and result['objective']>best:
            best=result['objective'];best_epoch=epoch+1;model.save(str(output/'encoder'));torch.save(head.state_dict(),output/'head.pt')
        print(json.dumps(dict(kind=kind,epoch=epoch+1,objective=result['objective'],guard=guard,best_epoch=best_epoch)),flush=True)
        if time.perf_counter()-start>120:break
    meta=dict(model_version=output.name,parent=str(BASE),dataset_manifest_sha256=sha(DATA/'manifest.json'),kind=kind,seed=42,learning_rate=5e-6,
        max_epochs=2,max_seconds=120,steps=steps,elapsed_seconds=time.perf_counter()-start,best_epoch=best_epoch,baseline_validation=base,history=history,
        objective='0.35 overall F1 + 0.35 macro F1 + 0.15 worst recall + 0.15 implicit recall - 0.5 safety FPR; validation only with English/Hinglish/safety guards',production=False)
    (output/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('build','train'));p.add_argument('--output',type=Path);p.add_argument('--kind',choices=('uniform','class','language_cluster'),default='uniform');a=p.parse_args()
    if a.action=='build':build()
    elif a.output:train_run(a.output,a.kind)
    else:p.error('--output required')
