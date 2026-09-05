import json
import math
import os
from functools import lru_cache
from pathlib import Path

from schemas.analysis import MLAnalysis
from ml.embeddings import get_embedding_model


MODEL_VERSION = "v1"
ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
CLASSIFIER_PATH = ARTIFACTS_DIR / "classifier.joblib"
EMBEDDING_MODEL_PATH = ARTIFACTS_DIR / "embedding_model"
METADATA_PATH = ARTIFACTS_DIR / "metadata.json"
V2_DIR = ARTIFACTS_DIR / "v2"


def _version():
    requested = os.getenv("NAZAR_ML_VERSION", "auto").lower()
    if requested not in ("auto", "v1", "v2"):
        raise ValueError("Unsupported local ML version")
    return ("v2" if (V2_DIR / "classifier.joblib").exists() else "v1") if requested == "auto" else requested


@lru_cache(maxsize=2)
def _load_model_bundle(version="v1"):
    classifier_path = V2_DIR / "classifier.joblib" if version == "v2" else CLASSIFIER_PATH
    metadata_path = V2_DIR / "metadata.json" if version == "v2" else METADATA_PATH
    if not classifier_path.exists() or not EMBEDDING_MODEL_PATH.exists():
        raise FileNotFoundError("ML artifacts have not been trained")

    import joblib

    # Only trusted local artifacts produced by the training command are loaded.
    if version == "v2":
        import hashlib
        metadata = json.loads(metadata_path.read_text())
        if metadata.get("model_version") != "v2" or metadata.get("classifier_sha256") != hashlib.sha256(classifier_path.read_bytes()).hexdigest():
            raise ValueError("Invalid v2 artifact metadata")
    classifier = joblib.load(classifier_path)
    embedding_model = get_embedding_model()
    model_version = version
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text())
        model_version = metadata.get("model_version", version)
    return embedding_model, classifier, model_version


def predict_scam_probability(text: str) -> MLAnalysis:
    model_version = None
    try:
        model_version = _version()
        embedding_model, classifier, model_version = _load_model_bundle(model_version)
        # A sentence embedding is a dense numeric representation of semantic meaning.
        embedding = embedding_model.encode([text], normalize_embeddings=True)
        tokenizer = getattr(embedding_model, "tokenizer", None)
        limit = getattr(embedding_model, "max_seq_length", None)
        truncated = False
        if tokenizer is not None and isinstance(limit, int):
            tokens = tokenizer(text, truncation=False, add_special_tokens=True, verbose=False)["input_ids"]
            truncated = len(tokens) > limit
        scam_class_index = list(classifier.classes_).index(1)
        probability = float(classifier.predict_proba(embedding)[0][scam_class_index])
        if not math.isfinite(probability) or not 0 <= probability <= 1:
            raise ValueError("Invalid classifier probability")
        from ml.neighbors import explain_neighbors
        neighbors = explain_neighbors(embedding_model, embedding[0], model_version)
        return MLAnalysis(
            available=True,
            input_truncated=truncated,
            semantic_neighbors=neighbors,
            scam_probability=probability,
            model_version=model_version,
        )
    except Exception:
        # ML is optional evidence: deterministic protection must remain available.
        return MLAnalysis(available=False, model_version=model_version)
