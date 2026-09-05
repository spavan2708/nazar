# Nazar

Nazar combines message, screenshot, audio and URL analysis with investigations and trusted-source guidance. The React/Next.js frontend connects to the Python/FastAPI backend.

## Local development

From the repository root, prepare and start the backend:

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
# First setup only: copy .env.example to .env if .env does not already exist.
.venv/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Use one backend worker: investigations are held in process memory and disappear on restart. They expire after one hour (cleanup occurs on the next investigation operation), with at most 100 investigations and 100 evidence items per investigation. This prototype does not provide persistent investigation storage.

In a separate terminal, from the repository root:

```bash
cd frontend
npm ci
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

Open http://localhost:3000. Set `NEXT_PUBLIC_API_URL` to the backend address when building for another environment; it is a public frontend setting.

## Optional analysis services

Backend settings are documented in [the environment template](../backend/.env.example). Preserve existing `.env` values when updating configuration.

- LLM analysis is disabled by default. To enable it, configure `LLM_ENABLED`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL` and the timeout. Extracted text may be sent to the configured provider when enabled.
- Screenshot OCR uses local Tesseract. On macOS, install `brew install tesseract tesseract-lang`. `OCR_LANGUAGES=eng+hin+tam` requests English, Hindi and Tamil; the service uses the installed subset. Screenshots require PNG, JPEG or WEBP, at most 5 MiB and 16 megapixels.
- Audio transcription uses local FFmpeg and whisper.cpp. On macOS, install `brew install ffmpeg whisper-cpp`. Place a multilingual Whisper model at `backend/stt/models/ggml-base.bin`, or configure `WHISPER_MODEL_PATH`. The default language is `auto`; English-only `.en` models do not support multilingual transcription. Audio accepts WAV, MP3, M4A and WEBM, at most 20 MiB and two minutes.

To download the multilingual audio model, run from `backend`:

```bash
mkdir -p stt/models
curl -fL https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin -o stt/models/ggml-base.bin
```

## Local models and trusted guidance

Retain the local embedding model in `backend/ml/artifacts/embedding_model` and the classifier artifacts. Normal application startup does not train or download models. `NAZAR_ML_VERSION=auto` selects v2 when its classifier exists, otherwise v1; set `v1` or `v2` to pin a version. Missing or invalid artifacts make the optional ML component unavailable. Restart the backend after replacing artifacts.

The retained [baseline training script](../backend/ml/train.py), [v2 training script](../backend/ml/train_v2.py), datasets and manifests provide reproducibility. With the existing local embedding model and baseline artifacts, run from `backend` to train into a fresh directory:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m ml.train_v2 --output ml/artifacts/v2-reproduction-new
```

For an initial v2 installation only, omit `--output` when the default v2 output directory does not already exist. Do not retrain as part of routine startup.

Trusted guidance uses [curated knowledge and provenance](../backend/rag/knowledge/PROVENANCE.md). Build its local index from `backend`:

```bash
.venv/bin/python -m rag.build_index
```

Keep `rag/knowledge/guidance.json`, `rag/index/vectors.npy` and `rag/index/metadata.json` together with the matching embedding model. Rebuild the index and restart after changing the knowledge or embedding model. Index building uses the local model; retrieval does not make network requests. `RAG_ENABLED=false` disables retrieval; `ML_EXPLANATIONS_ENABLED=false` disables synthetic training-example explanations. Neither feature changes the detector score.

## Verification and evaluation

From `backend`:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The optional real transcription test requires the audio tools and model:

```bash
NAZAR_REAL_AUDIO_TEST=1 .venv/bin/python -m unittest discover -s tests -p test_audio_analysis.py -v
```

Evaluation scripts recreate human-readable reports; retain their code, frozen datasets, results and authored findings. From `backend`:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m ml.train_v2 --evaluate-only
PYTHONPATH=. .venv/bin/python evaluation/explain_v12_1.py
PYTHONPATH=. .venv/bin/python evaluation/evaluate_v13.py
```

The error inspection reads frozen ML results and authored findings. Retrieval evaluation requires the local index. `evaluation/multilingual.py` regenerates the multilingual report and can call the configured LLM provider.

From `frontend`:

```bash
npm run lint
npm run design:check
npm run test:ui
npm run build -- --webpack
```

For frontend work, follow the permanent [design reference](../DESIGN.md), [design system](DESIGN_SYSTEM.md) and [agent workflow](AGENTS.md).

## Research and hardening workflow

Production remains the preserved v2 classifier with ML evidence thresholds 0.65 and 0.80. Rules use severity points; local classifier output and LLM evidence scores are distinct quantities, not real-world fraud probabilities. RAG references, semantic neighbors and specialist projections do not add risk. Optional signal classifiers and fine-tuned encoders are research artifacts and are not loaded by the application.

The [research dataset manifest](../backend/ml/data/hardening/manifest.json) freezes train/validation paths and hashes, while referencing the original unchanged 90-row test file. Related scenarios share groups across languages. Unknown signal annotations are `null`, distinct from an annotated empty list. New examples are explicitly synthetic and have not received native-speaker review. Training does not read final test content; it selects through grouped training folds before writing a selection receipt and evaluating the holdout. The old test has been examined during earlier development, so it is a regression benchmark, not independent acceptance evidence. The v2 baseline has seen the original training rows now included in research validation; its validation results are descriptive and must not be used as an independent comparison.

Run from `backend`, choosing a fresh output directory/file each time:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m ml.research --output evaluation/hardening/research-new
.venv/bin/python -m evaluation.quality_gate --output evaluation/hardening/end-to-end-new.json
.venv/bin/python -m evaluation.rag_quality --output evaluation/hardening/rag-new.json
```

The research command compares logistic regression and nested sigmoid-calibrated LR/SVM candidates using grouped folds. It saves classifier artifacts, hashes, selection metadata, all predictions, language/category metrics, threshold sweeps, Brier/ECE reliability bins, paired noise probes, latency and memory measurements as JSON. Exact/normalized/lexical/group split conflicts are blocking; high embedding similarity is flagged for review because proximity does not prove equivalence. Do not promote a model with unresolved leakage concerns. False negatives can miss scams; false positives cause warning fatigue. No threshold is automatically optimized or deployed.

Noise variants are correlated probes of their clean parent, not extra independent examples. The end-to-end gate reports incorrect warning decisions rather than changing labels. Its screenshot uses real OCR; its generated WAV uses real decoding with a stubbed transcript, so it does not measure speech-recognition accuracy.

To render the actual API fixture outputs through the frontend's static React checks, run from `frontend`:

```bash
NAZAR_E2E_RESULTS=../backend/evaluation/hardening/quality_gate.json npm run test:ui
```

Optional fine-tuning reuses the local multilingual MiniLM encoder with a binary classification head. From `backend`, `.venv/bin/python -m ml.finetune` prints estimates without training or downloading. Explicit `--train --output <fresh-directory>` enables bounded training: AdamW, fixed seed, up to five epochs, validation-loss early stopping and one best checkpoint. The default time budget is five minutes and is checked between batches; a single batch/checkpoint can exceed that deadline. CPU training may require 3–5 GiB RAM and tens of minutes for a full run. MPS is used only when requested and available. No checkpoint is promoted, calibrated or tested against final test data by this command.

`.venv/bin/python -m evaluation.llm_consistency` is a dry run. Adding `--live` explicitly permits eight semantic invocations by default (four synthetic cases repeated twice); transient retries can make up to 24 HTTP attempts. Results distinguish availability, risk band, intent, signals, requested actions and safety context. No live consistency results are implied by the dry run.

## Analysis boundaries and optional QR support

Text is limited to 10,000 characters, JSON bodies and provider responses to 128 KiB. Local-model truncation is disclosed in advanced analysis. API stage timings contain durations only; user text and embeddings are not cached for profiling. LLM signals must include exact input evidence spans; this checks attribution, not the correctness of an interpretation. The existing provider may retry transient failures up to three HTTP attempts within its socket-timeout budget. It makes one semantic invocation per normal text analysis and no per-specialist calls.

The typed orchestrator routes existing findings to text, identity, social-engineering, credential, payment, phishing, safety, guidance and explanation specialists. Screenshot/audio adapters add modality findings; campaign correlation consumes structured evidence once. These modules have no external-action tools or recursive execution. They never contact institutions, open suspicious links or initiate payments. Claimed identities remain claims.

For optional QR decoding:

```bash
# From backend
.venv/bin/python -m pip install -r requirements-vision.txt
```

Set `QR_ENABLED=true` in the backend environment. OpenCV runs in a disposable local subprocess with an eight-second timeout and bounded image dimensions. URL payloads reuse offline URL inspection; UPI payment payloads are parsed as metadata without executing them. QR evidence can survive OCR failure. Payment-only QR content does not imply a scam or validate the recipient. No logo recognition, visual impersonation classifier or VLM is installed. QR findings are retained with their evidence, while uploaded images/audio are not permanently saved.

Explicit Hindi/Tamil topic names can match curated topics lexically when cross-language cosine similarity is weak. Such matches supply guidance context only, never scam signals or risk. General words such as “bank” do not qualify. The guidance itself stays attributed to the original official publication.

Guidance includes its review date and a review-due flag after 180 days. This is a curation reminder, not live verification of source availability. No source is automatically downloaded or refreshed.

This remains a local prototype foundation: authentication, durable encrypted investigations, deployment rate limits, independently sourced/native-reviewed datasets and live browser acceptance remain necessary before a public deployment. Static rendering and webpack checks do not establish visual correctness at device sizes.
