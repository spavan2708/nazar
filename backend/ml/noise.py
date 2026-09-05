"""Deterministic, paired corruption probes; never count variants as independent data."""
import re
import random


def variants(text, seed=42):
    rng = random.Random(seed)
    words = text.split()
    # Sparse character corruption preserves most context and leaves negation intact.
    chars = list(text)
    candidates = [i for i,c in enumerate(chars) if c in 'OoIl']
    for i in rng.sample(candidates, min(len(candidates), max(1, len(text)//80))):
        chars[i] = {'O':'0','o':'0','I':'1','l':'1'}[chars[i]]
    plain = re.sub(r'[,.;:!?]', '', text)
    return {
        'ocr_character': ''.join(chars),
        'ocr_layout': '\n'.join(' '.join(words[i:i+5]) for i in range(0,len(words),5)),
        'ocr_spacing': text.replace(' ', '  ', 2),
        'ocr_clipped': text[:-max(1,len(text)//12)],
        'stt_punctuation': plain,
        'stt_filler': 'um ' + plain,
        'stt_repeat': ((words[0]+' ') if words else '') + plain,
        'stt_homophone': re.sub(r'\bcode\b', 'coat', plain, flags=re.I),
        'stt_digits': re.sub(r'\d{3,}', lambda m:' '.join(m[0]), plain),
    }
