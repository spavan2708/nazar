import json
from collections import Counter
from pathlib import Path

import joblib
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split

from ml.classifier import (
    ARTIFACTS_DIR,
    CLASSIFIER_PATH,
    EMBEDDING_MODEL_PATH,
    METADATA_PATH,
    MODEL_VERSION,
)


EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DATASET_PATH = Path(__file__).resolve().parent / "data" / "scam_training.json"
RANDOM_SEED = 42

CHALLENGE_SET = (
    "Pass me the number that just appeared on your handset.",
    "To restore access, download the support tool and let our technician connect.",
    "Never reveal verification numbers to callers.",
    "Would you like to join us for coffee after work?",
)


def train() -> dict:
    if CLASSIFIER_PATH.exists() or EMBEDDING_MODEL_PATH.exists():
        raise FileExistsError("Existing model artifacts must not be overwritten. Use versioned research training.")
    records = json.loads(DATASET_PATH.read_text())
    texts = [record["text"] for record in records]
    labels = [1 if record["label"] == "scam" else 0 for record in records]

    # The pretrained language model converts sentences into numeric semantic vectors.
    embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    embeddings = embedding_model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    train_embeddings, test_embeddings, train_labels, test_labels = train_test_split(
        embeddings,
        labels,
        test_size=0.25,
        random_state=RANDOM_SEED,
        stratify=labels,
    )

    classifier = LogisticRegression(
        random_state=RANDOM_SEED,
        class_weight="balanced",
        max_iter=1000,
    )
    classifier.fit(train_embeddings, train_labels)
    predictions = classifier.predict(test_embeddings)

    challenge_embeddings = embedding_model.encode(
        list(CHALLENGE_SET),
        normalize_embeddings=True,
    )
    challenge_probabilities = classifier.predict_proba(challenge_embeddings)[:, 1]

    metadata = {
        "model_version": MODEL_VERSION,
        "embedding_model": EMBEDDING_MODEL_NAME,
        "classifier": "LogisticRegression",
        "random_seed": RANDOM_SEED,
        "dataset_size": len(records),
        "label_distribution": dict(Counter(record["label"] for record in records)),
        "train_size": len(train_labels),
        "test_size": len(test_labels),
        "metrics": {
            "accuracy": accuracy_score(test_labels, predictions),
            "precision": precision_score(test_labels, predictions, zero_division=0),
            "recall": recall_score(test_labels, predictions, zero_division=0),
            "f1": f1_score(test_labels, predictions, zero_division=0),
            "confusion_matrix": confusion_matrix(test_labels, predictions).tolist(),
        },
        "challenge_predictions": [
            {"text": text, "scam_probability": float(probability)}
            for text, probability in zip(CHALLENGE_SET, challenge_probabilities)
        ],
        "limitations": (
            "Prototype dataset created for architecture validation; probabilities are not "
            "production-calibrated and the dataset is not representative of real-world prevalence."
        ),
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    embedding_model.save(str(EMBEDDING_MODEL_PATH))
    joblib.dump(classifier, CLASSIFIER_PATH)
    METADATA_PATH.write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))
    return metadata


if __name__ == "__main__":
    train()
