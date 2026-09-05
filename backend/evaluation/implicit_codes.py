"""Read-only regression/model evaluation; emits JSON to stdout, never trains.

Run from backend: LLM_ENABLED=false python -m evaluation.implicit_codes
The family is a development regression set, not an independent held-out benchmark.
"""
import json
from pathlib import Path
from unittest.mock import patch
import joblib
from fastapi.testclient import TestClient
from main import app
from ml.classifier import _load_model_bundle, _version
from ml.diagnostics import model_diagnostics
from ml.v2_experiments import metrics, probability
from schemas.semantic import SemanticAnalysis
from tests.implicit_code_cases import ATTACKS, SAFE


def evaluate():
    model, production, _ = _load_model_bundle(_version())
    texts = ATTACKS + SAFE
    embeddings = model.encode(texts, normalize_embeddings=True)
    candidates = {'production': production}
    path = Path(__file__).parent / 'hardening/research-1/classifier.joblib'
    if path.exists():
        candidates['research-1'] = joblib.load(path)
    predictions = {name: probability(classifier, embeddings) for name, classifier in candidates.items()}
    client = TestClient(app)
    with patch('services.analysis_service.analyze_semantics', return_value=SemanticAnalysis(available=False)):
        rows = []
        for i, text in enumerate(texts):
            response = client.post('/api/analyze/text', json={'text': text})
            response.raise_for_status()
            rows.append(dict(text=text, expected_otp=i < len(ATTACKS),
                models={name: float(values[i]) for name, values in predictions.items()}, api=response.json()))
    frozen = json.loads((Path(__file__).resolve().parents[1] / 'ml/data/eval_v2.json').read_text())
    vectors = model.encode([row['text'] for row in frozen], normalize_embeddings=True)
    return dict(diagnostics=model_diagnostics(), rows=rows,
        family_metrics={name: metrics([1]*len(ATTACKS)+[0]*len(SAFE), values) for name, values in predictions.items()},
        frozen_metrics={name: metrics([int(row['label']=='scam') for row in frozen], probability(classifier, vectors)) for name, classifier in candidates.items()})


if __name__ == '__main__':
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2))
