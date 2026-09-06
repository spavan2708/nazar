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
wheels rather than CUDA. Model files are never downloaded, rebuilt, or retrained.
Whisper is compiled for Linux from the matching v1.9.2 release. The macOS binaries
are never uploaded. OCR language data comes from Debian packages.

## Packaging and repeat deployment

Vercel CLI rejects individual source uploads larger than 100 MB. Run:

```sh
python3 backend/prepare_vercel_artifacts.py
vercel deploy --prod
```

The preparation command splits the two existing weight files into 64 MiB chunks
under ignored `backend/.runtime-upload/`. The container build reassembles them
and verifies SHA-256 before copying each model into a separate final image layer.
Separate layers respect VCR's 500 MB compressed-layer limit. Intermediate upload
chunks are not part of the final image. `.vercelignore` deliberately includes
these generated runtime chunks and excludes the original oversized files.

Deploy from this local artifact-complete working tree. A Git-only checkout does
not contain the ignored models and cannot reproduce this deployment by itself.
The CLI linked the existing GitHub repository when it created the project; a
future Git-triggered build also needs these artifacts before it can succeed.

`.vercelignore` and `.dockerignore` exclude environment files, virtualenvs,
node_modules, build caches, evaluation outputs, research checkpoints, and
development-only datasets. Approximately 3.6 GiB of local development/research
content is excluded. Required model files remain local and uncommitted.

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
