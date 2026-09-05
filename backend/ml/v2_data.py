"""Dataset contracts and contamination checks shared by training and tests."""
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from difflib import SequenceMatcher

DATA = Path(__file__).resolve().parent / 'data'
LANGUAGES = {'English', 'Hindi', 'Tamil', 'Hinglish', 'Tanglish', 'Mixed'}


def normalized(text):
    return re.sub(r'[^\w]', '', unicodedata.normalize('NFKC', text).casefold())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(records):
    if not isinstance(records, list) or not records:
        raise ValueError('Dataset must be a nonempty list')
    seen, ids = set(), set()
    for row in records:
        if not isinstance(row, dict) or not {'id','text','label','language','category','difficulty','source_type','notes','group'} <= row.keys():
            raise ValueError('Missing dataset fields')
        if not isinstance(row['text'], str) or not row['text'].strip() or row['label'] not in ('scam', 'safe') or row['language'] not in LANGUAGES:
            raise ValueError('Invalid text, label or language')
        if any(not isinstance(row[k], str) or not row[k].strip() for k in ('id','category','difficulty','source_type','notes','group')):
            raise ValueError('Invalid metadata')
        key = normalized(row['text'])
        if key in seen or row['id'] in ids:
            raise ValueError('Duplicate record')
        seen.add(key); ids.add(row['id'])
    if {row['label'] for row in records} != {'scam','safe'}:
        raise ValueError('Both classes required')


def validate_split(train, evaluation, legacy=()):
    validate(train); validate(evaluation)
    # Exact and near-duplicate lexical checks cannot establish semantic independence.
    for left in train + list(legacy):
        a = normalized(left['text'])
        for right in evaluation:
            b = normalized(right['text'])
            if a == b or SequenceMatcher(None, a, b, autojunk=False).ratio() >= .90:
                raise ValueError(f'Train/eval overlap: {left.get("id", "v1")} / {right["id"]}')
    if {r['group'] for r in train} & {r['group'] for r in evaluation}:
        raise ValueError('Split group overlap')


def load_frozen():
    manifest = json.loads((DATA / 'v2_manifest.json').read_text())
    for name, expected in manifest.items():
        if digest(DATA / name) != expected:
            raise ValueError('Frozen dataset hash mismatch: ' + name)
    train = json.loads((DATA / 'train_v2.json').read_text())
    evaluation = json.loads((DATA / 'eval_v2.json').read_text())
    legacy = json.loads((DATA / 'scam_training.json').read_text())
    validate_split(train, evaluation, legacy)
    return train, evaluation, manifest
