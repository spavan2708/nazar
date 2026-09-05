"""Small local-only challenge; run from backend with .venv/bin/python -m evaluation.evaluate_v11_1."""
import json
from pathlib import Path
from ml.classifier import predict_scam_probability
from schemas.signals import SignalCode
from services.text_analyzer import analyze_text
from services.risk_fusion import ML_MODERATE_THRESHOLD, ML_HIGH_THRESHOLD


def main():
    folder = Path(__file__).resolve().parent
    cases = json.loads((folder / 'v11_1_challenge.json').read_text())
    rows = []
    for case in cases:
        v3 = analyze_text(case['text'])
        v4 = predict_scam_probability(case['text'])
        probability = v4.scam_probability
        rows.append({**case, 'v3_score': v3.score, 'v3_signals': sorted(v3.signal_codes),
            'v3_sensitive': bool(v3.signal_codes & {SignalCode.OTP_REQUEST, SignalCode.CREDENTIAL_REQUEST}),
            'v4_available': v4.available, 'v4_probability': probability,
            'v4_band': 'unavailable' if probability is None else 'high' if probability >= ML_HIGH_THRESHOLD else 'moderate' if probability >= ML_MODERATE_THRESHOLD else 'below threshold'})
    result = {'note':'V3 and real local V4 measured independently; V5 is never invoked. Selected tiny challenge, not a real-world accuracy estimate.', 'v4_model_version': v4.model_version, 'rows':rows}
    (folder / 'v11_1_results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print('Cases:', len(rows))
    print('V3 sensitive matches:', sum(r['v3_sensitive'] == r['expected_sensitive'] for r in rows))
    print('V4 available:', sum(r['v4_available'] for r in rows))
    for expected in (True, False):
        subset = [r for r in rows if r['expected_sensitive'] == expected]
        print('Expected sensitive:', expected, 'count:', len(subset), 'V4 at moderate-or-high threshold:', sum(r['v4_band'] in ('high', 'moderate') for r in subset))
    print('Regression:', next(r for r in rows if r['category'] == 'regression'))


if __name__ == '__main__':
    main()
