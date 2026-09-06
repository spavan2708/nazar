"""Compare representative live local-layer results with a frozen quality report."""
import argparse
import json
from pathlib import Path
import httpx


def run(url, baseline, output):
    selected = {}
    for case in json.loads(baseline.read_text())['cases']:
        if case['modality'] == 'text':
            selected.setdefault((case['language'], case['label']), case)
    results = []
    with httpx.Client(base_url=url.rstrip('/'), timeout=300) as client:
        for case in selected.values():
            expected = case['analysis']
            response = client.post('/api/analyze/text', json={'text': expected['original_text']})
            response.raise_for_status()
            actual = response.json()
            # A remote provider must be disabled for a deterministic total-score comparison.
            assert not actual['semantic']['available'], 'Run local-layer parity before enabling Gemini'
            exact = all(actual[k] == expected[k] for k in ['score', 'risk_level', 'signals'])
            ml = actual['ml']['available'] and actual['ml']['model_version'] == expected['ml']['model_version']
            delta = abs(actual['ml']['scam_probability'] - expected['ml']['scam_probability']) if ml else None
            rag = [r['chunk_id'] for r in actual['grounding']['results']] == [r['chunk_id'] for r in expected['grounding']['results']]
            results.append({'id': case['id'], 'language': case['language'], 'label': case['label'],
                            'scores_labels_signals_equal': exact, 'ml_delta': delta, 'rag_sources_equal': rag,
                            'pass': exact and ml and delta < 1e-6 and rag})
            print(case['language'], case['label'], results[-1]['pass'], flush=True)
    output.write_text(json.dumps(results, indent=2))
    return all(r['pass'] for r in results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('baseline', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    raise SystemExit(0 if run(args.url, args.baseline, args.output) else 1)
