"""Versioned synthetic research corpus; build once, never edits legacy benchmarks.

python -m ml.hardening_data builds grouped splits and an auditable manifest.
Similarity is used only for leakage screening, never for assigning labels.
"""
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Literal
import numpy as np
from pydantic import Field
from ml.dataset import Example, ROOT, sha
from ml.embeddings import get_embedding_model

DATA = ROOT / 'hardening_v2'
SEED = 42


class ResearchExample(Example):
    schema_version: Literal[2] = 2
    difficulty: Literal['easy', 'medium', 'hard']
    source_type: Literal['synthetic_manual', 'synthetic_authored', 'synthetic_augmented', 'synthetic_translated']
    implicit_request: bool | None = None
    cluster_id: str = Field(min_length=1)
    translated_from: str | None = None
    # Keep existing string labels and language names so existing tools interoperate.


def normalized(text):
    value = unicodedata.normalize('NFKC', text).casefold()
    return ''.join(c for c in value if c.isalnum())


def breakdown(rows):
    return dict(n=len(rows), groups=len({r.get('cluster_id', r.get('group', r.get('id'))) for r in rows}),
        **{key:dict(Counter(str(r.get(key)) for r in rows)) for key in
           ('label','language','category','difficulty','source_type','safety_context','implicit_request','noise_type')},
        signal_support=dict(Counter(s for r in rows for s in (r.get('signals') or []))),
        annotations_unknown=sum(r.get('signals') is None for r in rows))


def legacy_audit():
    paths = [ROOT/'scam_training.json', ROOT/'train_v2.json', ROOT/'eval_v2.json',
             ROOT/'hardening/train.json', ROOT/'hardening/validation.json']
    result = {}
    for path in paths:
        rows=json.loads(path.read_text())
        result[str(path.relative_to(ROOT))] = dict(sha256=sha(path), **breakdown(rows),
            exact_duplicates=len(rows)-len({r['text'] for r in rows}),
            normalized_duplicates=len(rows)-len({normalized(r['text']) for r in rows}),
            implicit_category_proxy=sum(r.get('category') in {'implicit_sensitive','euphemistic','implicit_otp'} for r in rows),
            lexical_noise_proxy=sum(bool(re.search(r'\b(?:jldi|krdo|verifiction|bta)\b',r['text'])) for r in rows))
    return result


def authored():
    rows=[]; parents={}
    with (DATA/'scenarios.tsv').open() as handle:
        for i,r in enumerate(csv.DictReader(handle,delimiter='\t')):
            for label,column in [('scam','scam_text'),('safe','safe_text')]:
                rid=f'h2-s{i+1:03}-{label}'
                key=(r['cluster_id'],label); parent=parents.get(key)
                group='h2-'+r['cluster_id']
                rows.append(ResearchExample(id=rid,text=r[column],label=label,language=r['language'],
                    language_style=r['language'],category=r['category'] if label=='scam' else ('safety' if r['safety_context']=='true' else 'benign_support'),
                    difficulty='hard',source_type='synthetic_translated' if parent else 'synthetic_authored',
                    group=group,cluster_id=group,translated_from=parent,
                    signals=r['signals'].split(',') if label=='scam' else [],
                    safety_context=label=='safe' and r['safety_context']=='true',
                    implicit_request=label=='scam' and r['implicit_request']=='true',
                    notes='AI-authored/adapted synthetic scenario; paired opposite intent and translations grouped. No human or native-speaker review.').model_dump(mode='json'))
                parents.setdefault(key,rid)
    with (DATA/'controls.tsv').open() as handle:
        for i,r in enumerate(csv.DictReader(handle,delimiter='\t')):
            group='h2-control-'+r['cluster_id']
            rows.append(ResearchExample(id=f'h2-control-{i+1:03}',text=r['text'],label='safe',language=r['language'],
                language_style=r['language'],category=r['category'],difficulty='hard',source_type='synthetic_authored',
                group=group,cluster_id=group,signals=[],safety_context=r['safety_context']=='true',implicit_request=False,
                notes='AI-authored safe control, including quoted instructions; no native-speaker review.').model_dump(mode='json'))
    return rows


NOISE_TYPES=('misspelling','punctuation','lowercase','repeated_letter','ocr','stt','abbreviation','spacing','unicode')


def noise(text, kind):
    """Sparse changes; no clipping and no edits to negation words."""
    if kind=='punctuation': return re.sub(r'[,;:!?।.]','',text)
    if kind=='lowercase': return text.lower()
    if kind=='unicode': return text.replace(' ', '\u200b ',1)
    if kind=='spacing': return text.replace(' ', '  ',1)
    if kind=='ocr': return re.sub(r'\b(code|OTP|login)\b',lambda m:{'code':'c0de','OTP':'0TP','login':'l0gin'}[m[0]],text,count=1)
    if kind=='stt': return re.sub(r'\bcode\b','coat',text,count=1,flags=re.I)
    if kind=='abbreviation': return re.sub(r'\b(please|please|jaldi|pannunga|send karo)\b',lambda m:{'please':'pls','jaldi':'jldi','pannunga':'panunga','send karo':'send krdo'}[m[0]],text,count=1)
    if kind=='misspelling': return re.sub(r'\b(verification|number|password)\b',lambda m:{'verification':'verifiction','number':'numbr','password':'pasword'}[m[0]],text,count=1)
    if kind=='repeated_letter': return re.sub(r'\b(send|bhejo|seekiram|urgent)\b',lambda m:m[0]+m[0][-1],text,count=1)
    raise ValueError(kind)


def load(split):
    manifest=json.loads((DATA/'manifest.json').read_text()); entry=manifest['splits'][split]
    path=DATA/entry['file']
    if sha(path)!=entry['sha256']:raise ValueError('Dataset fingerprint mismatch')
    return [ResearchExample.model_validate(r).model_dump(mode='json') for r in json.loads(path.read_text())]


def load_frozen_v2():
    manifest = json.loads((DATA / 'manifest.json').read_text())
    path = ROOT / 'eval_v2.json'
    if sha(path) != manifest['frozen_v2_sha256']:
        raise ValueError('Protected v2 benchmark fingerprint mismatch')
    return json.loads(path.read_text())


def build():
    if (DATA/'manifest.json').exists(): raise FileExistsError('Version already frozen')
    audit=legacy_audit(); rows=[]
    for split in ('train','validation'):
        for r in json.loads((ROOT/'hardening'/f'{split}.json').read_text()):
            r = dict(r, difficulty='medium' if r['difficulty']=='standard' else r['difficulty'])
            rows.append(ResearchExample(**r, cluster_id=r['group']).model_dump(mode='json'))
    rows += authored()
    # These previously observed evaluations remain evaluation-only, never training.
    from tests.implicit_code_cases import ATTACKS,SAFE
    frozen=json.loads((ROOT/'eval_v2.json').read_text())
    protected=[dict(id='frozen-'+r['id'],text=r['text']) for r in frozen]
    protected += [dict(id=f'implicit-{i}',text=t) for i,t in enumerate(ATTACKS+SAFE)]
    for name in ('hardening/adversarial_cases.json','v11_1_challenge.json'):
        for i,r in enumerate(json.loads((ROOT.parents[1]/'evaluation'/name).read_text())):
            protected.append(dict(id=f'{name}-{i}',text=r['text']))
    encoder=get_embedding_model()
    X=np.asarray(encoder.encode([r['text'] for r in rows],normalize_embeddings=True,show_progress_bar=False))
    Z=np.asarray(encoder.encode([r['text'] for r in protected],normalize_embeddings=True,show_progress_bar=False))
    parent=list(range(len(rows)))
    def find(i):
        while parent[i]!=i: parent[i]=parent[parent[i]];i=parent[i]
        return i
    def union(i,j): parent[find(max(i,j))]=find(min(i,j))
    by_group={}; keys=[normalized(r['text']) for r in rows]; duplicates=[]; merges=[]
    similarities=X@X.T
    for i,r in enumerate(rows):
        if r['group'] in by_group: union(i,by_group[r['group']])
        else:by_group[r['group']]=i
        for j in range(i):
            exact=r['text']==rows[j]['text']; norm=keys[i]==keys[j]
            near=SequenceMatcher(None,keys[i],keys[j],autojunk=False).ratio()>=.90
            semantic=float(similarities[i,j])>=.95
            if norm:
                if r['label']!=rows[j]['label']: raise ValueError('Duplicate label conflict')
                duplicates.append(dict(left=rows[j]['id'],right=r['id'],exact=exact))
            if near or semantic or norm:
                union(i,j)
                if rows[j]['group']!=r['group']:
                    merges.append(dict(left=rows[j]['id'],right=r['id'],lexical=near,similarity=float(similarities[i,j])))
    quarantine=set(); overlap=[]
    protected_sim=X@Z.T
    for i,r in enumerate(rows):
        for j,p in enumerate(protected):
            near=SequenceMatcher(None,keys[i],normalized(p['text']),autojunk=False).ratio()>=.90
            sim=float(protected_sim[i,j])
            if near or sim>=.95:
                quarantine.add(find(i));overlap.append(dict(development=r['id'],protected=p['id'],lexical=near,similarity=sim))
    components=defaultdict(list)
    for i in range(len(rows)):components[find(i)].append(i)
    splits={k:[] for k in ('train','validation','test')}; seen=set(); assigned={}; removed=[]
    for root,indices in components.items():
        members=sorted(rows[i]['id'] for i in indices)
        cluster='cluster-'+hashlib.sha256('|'.join(members).encode()).hexdigest()[:16]
        # Legacy examples already seen in previous model fitting cannot become a new holdout.
        legacy=any(not rows[i]['id'].startswith('h2-') for i in indices)
        bucket=int(hashlib.sha256((str(SEED)+cluster).encode()).hexdigest()[:8],16)%10
        split='train' if legacy or bucket>=4 else ('validation' if bucket>=2 else 'test')
        assigned[cluster]=dict(split=split,legacy=legacy,members=members,quarantined=root in quarantine)
        for i in indices:
            if root in quarantine:
                removed.append(rows[i]['id']);continue
            if keys[i] in seen:continue
            seen.add(keys[i]);r=dict(rows[i],group=cluster,cluster_id=cluster);splits[split].append(r)
    # At most one variant per selected parent; only training gets augmentation.
    clean_n=len(splits['train']);aug=[];raw_seen={r['text'] for r in splits['train']}
    ordered=sorted(splits['train'],key=lambda r:hashlib.sha256(r['id'].encode()).hexdigest())
    target=clean_n//5
    for kind in NOISE_TYPES:
        quota=target//len(NOISE_TYPES);made=0
        for r in ordered:
            if made>=quota:break
            if any(a['parent_id']==r['id'] for a in aug):continue
            text=noise(r['text'],kind)
            if text in raw_seen:continue
            raw_seen.add(text);made+=1
            aug.append(dict(r,id=r['id']+'-'+kind,text=text,parent_id=r['id'],source_type='synthetic_augmented',noise_type=kind,
                translated_from=None,notes='Controlled synthetic text corruption; parent cluster preserved; not an independent observation.'))
    splits['train']+=aug
    assert all(splits.values()), 'Insufficient independent groups after leakage screening'
    for split,rs in splits.items():
        for r in rs:ResearchExample.model_validate(r)
        p=DATA/f'{split}.json';p.write_text(json.dumps(rs,ensure_ascii=False,indent=2)+'\n')
    # Flag lower-similarity pairs for review; do not claim zero semantic leakage.
    id_split={r['id']:k for k,rs in splits.items() for r in rs}; review=[]
    for i,r in enumerate(rows):
        for j in range(i):
            if r['id'] in id_split and rows[j]['id'] in id_split and id_split[r['id']]!=id_split[rows[j]['id']] and similarities[i,j]>=.90:
                review.append(dict(left=rows[j]['id'],right=r['id'],similarity=float(similarities[i,j])))
    manifest=dict(version='hardening-v2',schema_version=2,seed=SEED,
        provenance='AI-authored synthetic and adapted translations; zero newly human/native-reviewed rows.',
        policy='Group connected components before splitting. Legacy components training-only. Clean new test frozen before fitting. .90 lexical/.95 cosine merges; protected overlap quarantines entire component. Train-only augmentation <=20% of clean train.',
        source_hashes={p.name:sha(p) for p in (DATA/'scenarios.tsv',DATA/'controls.tsv')},
        frozen_v2_sha256=sha(ROOT/'eval_v2.json'),legacy_audit=audit,
        counts={k:breakdown(v) for k,v in splits.items()},
        splits={k:dict(file=f'{k}.json',sha256=sha(DATA/f'{k}.json')) for k in splits},
        quality=dict(input_clean_rows=len(rows),normalized_duplicates=duplicates,quarantined_ids=removed,
            protected_overlap=overlap,component_merges=merges,components=assigned,semantic_review_pairs=review,
            caveat='Cosine grouping is conservative screening, not proof that all paraphrases were found. Augmentations intentionally resemble parents inside training only.'),
        acceptance='No automatic promotion. New test is synthetic, not independent native-reviewed field data.')
    (DATA/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(counts={k:len(v) for k,v in splits.items()},groups={k:len({r['group'] for r in v}) for k,v in splits.items()},quarantined=len(removed),duplicates=len(duplicates),semantic_review_pairs=len(review)),indent=2))


if __name__=='__main__':build()
