"""Deterministic import of authored records; no API generation or test-set edits."""
import csv
import hashlib
import json
from collections import defaultdict
from ml.dataset import DATA, ROOT, Example, sha, quality


def build():
    if (DATA/'manifest.json').exists():
        raise FileExistsError('Dataset already frozen; create a new version to revise it')
    rows=[]
    for r in json.loads((ROOT/'train_v2.json').read_text()):
        rows.append(Example(**r, language_style=r['language'], signals=None,
            safety_context=None).model_dump(mode='json'))
    with (DATA/'authored.tsv').open() as handle:
        for i,r in enumerate(csv.DictReader(handle,delimiter='\t')):
            rows.append(Example(id=f'hardening-{i+1:03}', text=r['text'], label=r['label'],
                language=r['language'], language_style=r['language'], category=r['category'],
                difficulty='hard', source_type='synthetic_authored', group='authored-'+r['group'],
                signals=r['signals'].split(',') if r['signals'] else [], safety_context=r['safety_context']=='true',
                notes='AI-authored synthetic scenario, not observed fraud; no native-speaker review. Matched scenarios share groups.').model_dump(mode='json'))
    # Related translations must share folds, even across distinct scenario groups.
    families={'hi-notification':'digits','ta-digits':'digits','hl-digits':'digits','tl-digits':'digits','mh-digits':'digits','mt-digits':'digits',
        'hi-qr':'refund','ta-upi':'refund','hl-refund':'refund','tl-refund':'refund',
        'hi-job':'job','ta-job':'job','hl-job':'job','tl-job':'job',
        'hi-control':'control','ta-permission':'control','hl-control':'control','tl-control':'control',
        'hi-profit':'profit','ta-profit':'profit','hi-password':'mail','ta-mail':'mail','mh-secret':'mail','mt-secret':'mail',
        'mh-pay':'salary','mt-pay':'salary'}
    for r in rows:
        key=r['group'].removeprefix('authored-')
        if key in families:r['group']='authored-multilingual-'+families[key]
    splits={'train':[], 'validation':[]}
    for r in rows:
        split='validation' if int(hashlib.sha256(r['group'].encode()).hexdigest()[:8],16)%5==0 else 'train'
        splits[split].append(r)
    report=quality(splits)
    if report['blocking_cross_split_overlaps']:raise ValueError(report['blocking_cross_split_overlaps'])
    manifest={'version':'hardening-1','seed':42,'authored_sha256':sha(DATA/'authored.tsv'),
        'policy':'Group-hash train/validation split; original 90-row test remains immutable. Test has been inspected historically and is a regression benchmark, not an independent acceptance set.', 'splits':{}}
    for split,records in splits.items():
        p=DATA/f'{split}.json';p.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
        manifest['splits'][split]={'path':str(p.relative_to(ROOT)),'sha256':sha(p),'n':len(records)}
    p=ROOT/'eval_v2.json'
    manifest['splits']['test']={'path':'eval_v2.json','sha256':sha(p),'n':90}
    (DATA/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':build()
