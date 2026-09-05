"""Safe local developer diagnostics. Run: python -m ml.diagnostics.

Loads the selected bundle in this process; does not claim another server's state.
No credentials, provider URLs, or user messages are included.
"""
import hashlib
import json
from ml.classifier import (
    _version, _load_model_bundle, V2_DIR, CLASSIFIER_PATH,
    METADATA_PATH, EMBEDDING_MODEL_PATH, ARTIFACTS_DIR,
)
from services.risk_fusion import ML_MODERATE_THRESHOLD, ML_HIGH_THRESHOLD


def model_diagnostics():
    version = _version()
    path = V2_DIR / 'classifier.joblib' if version == 'v2' else CLASSIFIER_PATH
    metadata_path = V2_DIR / 'metadata.json' if version == 'v2' else METADATA_PATH
    info = dict(selected_version=version, artifact_path=str(path),
                embedding_path=str(EMBEDDING_MODEL_PATH),
                thresholds={'moderate': ML_MODERATE_THRESHOLD, 'high': ML_HIGH_THRESHOLD})
    try:
        embedding, classifier, loaded = _load_model_bundle(version)
        metadata = json.loads(metadata_path.read_text())
        data_dir = ARTIFACTS_DIR.parent / 'data'
        info.update(loaded=True, model_version=loaded,
                    classifier=type(classifier).__name__,
                    classifier_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    embedding_model=metadata.get('embedding_model'),
                    max_seq_length=embedding.max_seq_length,
                    normalize_embeddings=True,
                    dataset='train_v2.json' if version == 'v2' else 'scam_training.json',
                    dataset_hashes=metadata.get('dataset_hashes', {}),
                    dataset_hashes_match=all(
                        (data_dir / name).exists() and hashlib.sha256((data_dir / name).read_bytes()).hexdigest() == digest
                        for name, digest in metadata.get('dataset_hashes', {}).items()))
    except Exception as error:
        info.update(loaded=False, error_type=type(error).__name__)
    return info


if __name__ == '__main__':
    print(json.dumps(model_diagnostics(), indent=2))
