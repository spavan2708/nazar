import json
from functools import lru_cache
from pathlib import Path

from schemas.analysis import MLAnalysis


MODEL_VERSION = "v1"
ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
CLASSIFIER_PATH = ARTIFACTS_DIR / "classifier.joblib"
EMBEDDING_MODEL_PATH = ARTIFACTS_DIR / "embedding_model"
METADATA_PATH = ARTIFACTS_DIR / "metadata.json"


@lru_cache(maxsize=1)
def _load_model_bundle():
    if not CLASSIFIER_PATH.exists() or not EMBEDDING_MODEL_PATH.exists():
        raise FileNotFoundError("ML artifacts have not been trained")

    import joblib
    from sentence_transformers import SentenceTransformer

    embedding_model = SentenceTransformer(
        str(EMBEDDING_MODEL_PATH),
        local_files_only=True,
    )
    classifier = joblib.load(CLASSIFIER_PATH)
    model_version = MODEL_VERSION
    if METADATA_PATH.exists():
        metadata = json.loads(METADATA_PATH.read_text())
        model_version = metadata.get("model_version", MODEL_VERSION)
    return embedding_model, classifier, model_version


def predict_scam_probability(text: str) -> MLAnalysis:
    try:
        embedding_model, classifier, model_version = _load_model_bundle()
        # A sentence embedding is a dense numeric representation of semantic meaning.
        embedding = embedding_model.encode([text], normalize_embeddings=True)
        scam_class_index = list(classifier.classes_).index(1)
        probability = float(classifier.predict_proba(embedding)[0][scam_class_index])
        return MLAnalysis(
            available=True,
            scam_probability=probability,
            model_version=model_version,
        )
    except Exception:
        # ML is optional evidence: deterministic protection must remain available.
        return MLAnalysis(available=False, model_version=MODEL_VERSION)
