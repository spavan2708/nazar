"""Run existing V3/V4/V5 on fixed synthetic examples; output no provider secrets."""
import argparse
from pathlib import Path

from evaluation.multilingual_cases import CASES
from ml.classifier import predict_scam_probability
from services.language_detection import identify_language
from services.llm.semantic_analyzer import analyze_semantics_with_diagnostics
from services.risk_fusion import fuse_risk
from services.text_analyzer import analyze_text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("evaluation/V7_RESULTS.md"))
    args = parser.parse_args()
    lines = [
        "# Nazar V7 multilingual evaluation", "",
        "14 synthetic, hand-authored examples; no retraining. This is a smoke evaluation, not an accuracy estimate or a representative benchmark.", "",
        "V4 uses the existing local paraphrase-multilingual-MiniLM-L12-v2 embeddings and v1 LogisticRegression (48-example prototype training dataset). Scores below are actual outputs, not calibrated probabilities or guarantees of language support.", "",
        "V5 uses the configured provider. Unavailable entries are failures/unavailability, not zero semantic risk. Only safe diagnostic categories are retained; provider messages, keys and headers are omitted.", "",
        "| Example | Expected | Language hint | V3 score | V4 probability | V5 risk / status | Final score / label |",
        "|---|---|---|---:|---:|---|---|",
    ]
    details = []
    available = 0
    for name, expected, text in CASES:
        v3 = analyze_text(text)
        v4 = predict_scam_probability(text)
        v5, diagnostic = analyze_semantics_with_diagnostics(text)
        result = fuse_risk(v3, v4, v5)
        available += int(v5.available)
        probability = f"{v4.scam_probability:.3f}" if v4.available else "unavailable"
        semantic = f"{v5.risk_score:.3f}" if v5.available else f"unavailable ({diagnostic.category if diagnostic else 'disabled/unconfigured'})"
        lines.append(f"| {name} | {expected} | {identify_language(text).detected_language} | {v3.score} | {probability} | {semantic} | {result.score} / {result.risk_level} |")
        details += [f"## {name}", "", text, "", "V3 canonical signals: " + (", ".join(sorted(code.value for code in v3.signal_codes)) or "none"), "V5 canonical signals: " + (", ".join(signal.code.value for signal in v5.signals) if v5.available and v5.signals else "none / unavailable"), ""]
        print(f"{name}: V3={v3.score}, V4={probability}, V5={semantic}, final={result.score}/{result.risk_level}", flush=True)
    lines += ["", f"V5 available on {available}/{len(CASES)} examples.", "",
        "Do not infer accuracy from this small set. Transliterations, dialects, negation, complex code-switching and OCR errors need much broader evaluation. V3 recognizes a small number of canonical concepts. Language hints are heuristic and do not change scores. V4 can process the scripts but its small scam classifier may miss scams or flag safe messages. V5 reliability depends on provider availability and must be evaluated separately when unavailable.", ""]
    args.output.write_text("\n".join(lines + details), encoding="utf-8")


if __name__ == "__main__":
    main()
