# Nazar Vercel deployment

One Vercel project uses Services: Next.js in `frontend/`, and a Linux container
running the existing FastAPI app in `backend/`. `/api/*` and `/health` route to
FastAPI; other requests route to Next.js. Production browser requests use the
same origin unless `NEXT_PUBLIC_API_URL` is explicitly supplied. Local development
continues to use port 8000.

## Runtime inventory

| Classification | Files/dependencies | Reason |
| --- | --- | --- |
| Required | `ml/artifacts/embedding_model/` (about 465 MiB) | Existing multilingual MiniLM, shared by classifier and RAG |
| Required | `ml/artifacts/v2/classifier.joblib`, `metadata.json` | Current auto-selected v2 production classifier and hash validation |
| Retained | v1 classifier and metadata | Existing fallback/version option; not retrained |
| Required | `ml/data/train_v2.json`, `v2_manifest.json` | Synthetic neighbor explanations and provenance checks |
| Required | `rag/index/metadata.json`, `vectors.npy`, `rag/knowledge/guidance.json` | Existing retrieval index and curated guidance |
| Required | `rag/build_index.py`, knowledge/schema modules | Retrieval imports validation helpers from these modules |
| Required | `stt/models/ggml-base.bin` (about 141 MiB) | Existing multilingual speech model |
| Required | whisper.cpp v1.9.2, FFmpeg/ffprobe | Native local speech transcription/decoding |
| Required | Tesseract plus eng/hin/tam packs | Screenshot OCR |
| Required | OpenCV headless and `services/qr_worker.py` | Isolated QR decoding subprocess |
| Development/research | `ml/artifacts/research/`, `v2-reproduction/`, evaluation outputs, hardening/recovery datasets | Retained locally; excluded from deployment |
| Uncertain/retained | Other ML research/training Python modules and metadata | Conservative cleanup; no behavior changes to justify removal |

The Python image pins the local major inference dependencies, using CPU Torch
wheels rather than CUDA. Exact preserved model files are downloaded during the image build, never rebuilt or retrained.
Whisper is compiled for Linux from the matching v1.9.2 release. The macOS binaries
are never uploaded. OCR language data comes from Debian packages.

## Runtime artifact releases and repeat deployment

Published release: [runtime-artifacts-2026-09-06.1](https://github.com/spavan2708/nazar/releases/tag/runtime-artifacts-2026-09-06.1).
The manifest pins its exact versioned asset URLs and original SHA-256 hashes.
GitHub's API reported `immutable: false` when verified on 2026-09-06. Treat the
release as fixed: do not replace or remove its assets. Checksum pinning rejects any
changed bytes, but cannot prevent deletion. Retain an independent backup.

`backend/runtime_artifacts/manifest.json` records the source Git commit, bundle
version, destination paths relative to `backend/`, exact byte sizes, file SHA-256
hashes, and archive SHA-256 hashes. Public versioned GitHub Release assets
hold these archives outside Git history:

- `nazar-minilm.tar.gz`: complete existing MiniLM directory, including tokenizer,
  configs and README; every file except README participates in the RAG fingerprint.
- `nazar-classifiers.tar.gz`: exact v1 and v2 classifiers and matching metadata.
- `nazar-whisper.tar.gz`: exact multilingual `ggml-base.bin`.

Existing tracked RAG index/knowledge and neighbor data remain supplied by Git.
No model is loaded, saved, reserialized, or trained by artifact preparation.

The one-time preparation command is `python3 backend/runtime_artifacts/prepare.py`.
It refuses to overwrite an existing version or manifest. Archives are written to
ignored `backend/.runtime-artifacts/runtime-artifacts-2026-09-06.1/`; the old
`.runtime-upload` workflow is obsolete and remains ignored. Neither directory
is sent to Vercel or Docker. The legacy chunk script is not used by deployment.

### Published assets and future versions

The three assets above are published and their actual download URLs are recorded
in the manifest. No publication step remains for this version. Never use `latest`
or expiring signed URLs. Future artifact changes require a new version and fresh
hash verification; enable GitHub release immutability before publishing future
releases. Commit, push and deployment remain separate approval steps.

The Docker models stage downloads the pinned assets over HTTPS without secrets,
checks each archive's byte count and SHA-256, rejects paths outside the manifest,
duplicate entries and nonregular members, then verifies every extracted file.
Downloads use at most three attempts, a 60-second socket timeout and bounded
exponential retry delays; archive sizes are bounded by the manifest.
Only verified files are copied into separate final layers. Missing URLs, missing
assets, or invalid checksums fail the build. Production inference remains offline
with `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`.

Offline archive validation:

```sh
python3 backend/runtime_artifacts/download.py \
  --archive-dir backend/.runtime-artifacts/runtime-artifacts-2026-09-06.1 \
  --destination /tmp/nazar-artifact-verification
```

Use an empty destination. Omit `--archive-dir` to validate real release downloads.
A clean Git checkout plus public release access supplies all runtime artifacts during Git-triggered Docker builds.
No local ignored inputs or private download credentials are required. Retain old
versioned releases and an independent backup; rollback selects the old code and
its pinned manifest. Do not overwrite an artifact version.

The initial download is about 606 MiB uncompressed; cache reuse is optional.
Keep MiniLM and Whisper in separate image layers to respect the existing VCR
500 MB compressed-layer limit. Network availability, build duration, dependency
installation and the existing Vercel size/runtime limits still apply.

Environment files, local model copies, virtualenvs, build caches and research
artifacts remain excluded from the deployment context.

## Environment and security

`VERCEL_SUPPORT_LARGE_FUNCTIONS=1` is configured in Vercel production for the
complete AI backend. Gemini configuration is transferred directly from existing
local backend settings to Vercel environment storage; the API key is a Secret.
No secret is a `NEXT_PUBLIC_*` value, Docker build argument, or source literal.
The image defaults to Gemini disabled if no runtime override is supplied.

The container enables existing QR functionality, all three OCR languages, offline
Hugging Face loading, and the current v2 classifier. Other existing runtime defaults
are preserved. FastAPI debug mode is off; access logging is disabled. Existing
localhost-only CORS remains restricted; same-origin production calls need no CORS
exception. Top-level routing does not expose backend `/docs` or `/openapi.json`.

## Production verification

Production URL: https://nazar-one-black.vercel.app

Live HTTP checks passed for homepage and eight Next.js assets, health, message,
URL, v2 ML and neighbor explanations, RAG, English OCR, QR decoding, real Whisper
transcription, and investigation creation/add-evidence/retrieval. Tesseract reports
eng/hin/tam installed. Twelve safe/scam samples across English, Hindi, Tamil,
Hinglish, Tanglish, and mixed language matched local risk scores, labels, signals,
and RAG source selection; ML differences were below 1e-6 across operating systems.
The live audio transcript correctly recovered the synthetic password request.

## Validation record

- Initial and final backend suites: 215 tests, 214 passed, 1 optional STT skip.
- Separate real local Whisper integration: passed.
- Initial and final lint, TypeScript, design-contract and static UI checks: passed.
- Local production Webpack build: passed. Local Turbopack was blocked by worker
  port permissions even after escalation; Vercel's actual Turbopack build passed.
- Initial and final quality gate: 270/270 valid contracts, 203/270 label agreement.
  Text and adversarial analyses are identical after excluding timings.
- Local dependency check and source credential-pattern scan: passed.
- `deploy/smoke.py` checks live HTML/assets, health, text/ML/RAG, URL, OCR/QR,
  investigation creation/evidence/retrieval, and optional synthetic speech.

## Operational limits

Investigations remain process-memory only, bounded by the original TTL and count
limits. Restart, scale-down, and routing to another instance can lose access to an
investigation. No persistence or instance affinity is promised.

Vercel request-size and execution-duration limits still apply. The app's local
5 MiB image and 20 MiB audio limits do not override platform ingress limits.
Cold starts include local model loading. Gemini remains an optional remote provider
and may fail independently of the local analysis layers.

No browser was connected to the available Browser tool during this deployment;
HTTP smoke tests do not certify visual layout, interactions, or browser console
behavior. No Git commit or push was performed.

References: [Services](https://vercel.com/docs/services),
[container images](https://vercel.com/docs/functions/container-images),
[VCR limits](https://vercel.com/docs/container-registry/limits-and-pricing),
[Large Functions](https://vercel.com/changelog/vercel-functions-can-now-be-up-to-5-gb-in-package-size).
