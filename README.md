# Nazar

**One warning before one wrong click.**

Nazar is a multimodal scam-intelligence platform that helps users analyze suspicious messages, links, screenshots, calls, QR codes, and related digital interactions before they share sensitive information, open a link, install software, or make a payment.

Rather than treating every suspicious interaction independently, Nazar can connect multiple pieces of evidence and identify how a potential social-engineering campaign is progressing.

**Live Application:** https://nazar-one-black.vercel.app

---

## Overview

Digital scams rarely happen through a single isolated message.

An attacker may first impersonate a bank, create urgency, send a verification link, request an OTP, and eventually attempt account takeover or payment extraction.

Traditional scam detectors often analyze each interaction independently.

Nazar approaches the problem differently.

It combines multiple independent intelligence layers to analyze individual evidence while also correlating related interactions into an evolving investigation.

The system currently supports:

- Messages
- URLs
- Screenshots
- QR codes
- Audio / call recordings
- Multi-evidence investigations

---

## Core Idea

Nazar follows a **Local-First, Multi-Layer Intelligence** architecture.

> **No single AI model decides the result. Multiple independent intelligence layers contribute evidence.**

The system combines:

- Deterministic scam detection
- Locally trained machine learning
- Optional LLM semantic analysis
- OCR
- Speech transcription
- Offline URL intelligence
- QR extraction
- Trusted-source retrieval
- Cross-interaction campaign correlation
- Explainable risk analysis

This architecture allows Nazar to continue functioning even when an optional intelligence source is unavailable.

---

## Key Features

### 1. Message Analysis

Nazar analyzes suspicious text for common social-engineering patterns such as:

- Urgency and pressure
- Bank impersonation
- Government impersonation
- OTP requests
- Credential requests
- Payment requests
- Account threats
- Identity-verification pretexts
- Remote-access requests
- Investment promises

The detector is context-aware and attempts to distinguish malicious requests from legitimate safety advice.

For example:

> "Send me the OTP immediately."

and

> "Never share your OTP with anyone."

should not be treated as equivalent messages.

---

### 2. Machine Learning Detection

Nazar includes a locally trained scam classifier.

The production classifier uses:

- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- Multilingual sentence embeddings
- Logistic Regression
- A fixed decision threshold
- Semantic-neighbor retrieval for explainability

The Logistic Regression classifier was trained specifically for Nazar.

The MiniLM encoder itself is pretrained and is used to generate multilingual semantic embeddings.

### Production Model Evaluation

The frozen evaluation set contains 90 examples:

- 45 scam
- 45 safe

| Metric | Result |
| --- | ---: |
| Accuracy | 78.9% |
| Precision | 86.1% |
| Recall | 68.9% |
| F1 Score | 76.5% |
| ROC-AUC | 89.0% |
| PR-AUC | 90.8% |

These results come from a small synthetic/partly translated evaluation dataset and should **not** be interpreted as real-world fraud detection accuracy.

The classifier output is also **not treated as a calibrated probability that fraud occurred**.

Experimental encoder fine-tuning has also been explored separately, but experimental models are not automatically promoted to production when multilingual subgroup performance regresses.

---

### 3. LLM Semantic Analysis

Nazar can optionally use an LLM as an additional semantic reasoning layer.

The semantic analyzer extracts structured information including:

- Intent
- Social-engineering tactics
- Requested actions
- Claimed identity
- Canonical scam signals
- Safety context
- Risk evidence
- Human-readable explanations

The LLM does **not** independently control the final result.

If the remote semantic service is unavailable, Nazar continues using deterministic detection, ML, URL analysis, RAG, and other available evidence.

This graceful degradation is intentional.

---

### 4. Screenshot Intelligence

Users can upload screenshots for analysis.

Nazar performs local OCR using **Tesseract** with support for:

- English
- Hindi
- Tamil

Extracted text is passed through the same shared scam-analysis pipeline used for normal messages.

Supported image formats include:

- PNG
- JPEG
- WEBP

Nazar currently performs OCR and QR extraction from images. It does not claim to visually verify brands, sender identities, or interface authenticity.

---

### 5. QR Code Analysis

Nazar uses OpenCV to detect QR codes contained in uploaded images.

When a QR code contains a URL, Nazar extracts the destination without opening it and passes it through the offline URL intelligence engine.

This allows suspicious QR destinations to be inspected without visiting them.

---

### 6. Audio and Call Analysis

Nazar supports uploaded audio evidence.

Audio is processed locally using:

- FFmpeg
- `whisper.cpp`

The resulting transcript is passed into the shared scam-analysis pipeline.

Supported formats include:

- WAV
- MP3
- M4A
- WEBM

Nazar analyzes transcript evidence only. It does not claim to identify or verify the speaker.

---

### 7. Offline URL Intelligence

Nazar analyzes URL structure without visiting the destination.

The URL engine can identify indicators such as:

- Non-HTTPS URLs
- Raw IP-address hosts
- Unusual ports
- Login and verification wording
- Credential-heavy paths
- Punycode / IDN indicators
- Suspicious hostname structures
- Complex query strings
- URL shorteners

This analysis is intentionally offline.

Nazar does **not** fetch the webpage, follow redirects, execute page content, query DNS, or claim external reputation information unless such functionality is explicitly added in the future.

Structural indicators represent reasons to verify a URL, not proof that a website is malicious.

---

### 8. Trusted Guidance with RAG

Nazar includes a local Retrieval-Augmented Generation (RAG) layer.

Trusted guidance is retrieved from curated cybersecurity and financial-safety sources.

Current references include guidance from organizations such as:

- CERT-In
- State Bank of India
- Delhi Police Cyber Cell

Relevant guidance is selected based on detected scam signals, topics, and attack stages.

RAG guidance is **score-independent**.

Retrieved information helps explain what a user should verify or avoid, but it does not artificially increase the scam score.

---

## Cross-Interaction Investigation

One of Nazar's central features is its ability to connect related interactions.

Instead of asking only:

> "Is this message suspicious?"

Nazar can also ask:

> "What is happening across this entire sequence?"

An investigation can contain multiple pieces of evidence and maintain structured state across them.

For example:

```text
Interaction 1
"Your bank account will be blocked unless you verify immediately."

        ↓

Detected:
Bank Impersonation
Urgency
Account Threat
Verification Pretext

        ↓

Interaction 2
"Send the 6 digit OTP you received."

        ↓

Detected:
OTP Request

        ↓

Combined Investigation

IMPERSONATION
        ↓
URGENCY / PRESSURE
        ↓
VERIFICATION PRETEXT
        ↓
AUTHENTICATION TAKEOVER
```

Nazar therefore distinguishes between the **risk of individual evidence** and the **progression of the overall interaction sequence**.

---

## Attack-Stage Tracking

Nazar can currently represent stages including:

```text
IMPERSONATION

URGENCY_OR_PRESSURE

VERIFICATION_PRETEXT

LINK_REDIRECTION

CREDENTIAL_HARVESTING

PAYMENT_EXTRACTION

REMOTE_ACCESS

AUTHENTICATION_TAKEOVER

INVESTMENT_LURE
```

Stage progression describes supported request patterns.

It does not claim that an account was actually compromised or that a payment occurred.

---

## Explainability

Nazar is designed to expose why a result was produced.

Analysis responses can include information from:

```text
Deterministic Rules
        │
        ├── Detected Signals
        │
Machine Learning
        │
        ├── Classifier Score
        ├── Evidence Level
        └── Semantic Neighbors
        │
LLM Semantic Analysis
        │
        ├── Intent
        ├── Tactics
        ├── Requested Actions
        └── Signals
        │
URL Intelligence
        │
        └── Structural Indicators
        │
Trusted Guidance
        │
        └── Relevant Safety References
        │
        ▼
Fused Explanation
```

Nazar can also describe agreement between intelligence sources.

Examples include:

- `STRONG_AGREEMENT`
- `PARTIAL_AGREEMENT`
- `RULES_ONLY`
- `ML_ONLY`
- `LLM_ONLY`
- `CONFLICTING`
- `INSUFFICIENT_EVIDENCE`

This makes disagreements between detectors visible instead of hiding them behind a single opaque number.

---

## System Architecture

```text
                         ┌─────────────────────────┐
                         │          User           │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │      Next.js UI         │
                         │                         │
                         │ Message │ URL │ Image   │
                         │ Audio   │ Investigation │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │       FastAPI API       │
                         └────────────┬────────────┘
                                      │
             ┌────────────────────────┼────────────────────────┐
             │                        │                        │
             ▼                        ▼                        ▼
    ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
    │ Deterministic   │      │ Local ML        │      │ Optional LLM    │
    │ Rules Engine    │      │ Classifier      │      │ Semantic Layer  │
    └────────┬────────┘      └────────┬────────┘      └────────┬────────┘
             │                        │                        │
             └────────────────────────┼────────────────────────┘
                                      │
                                      ▼
                           ┌─────────────────────┐
                           │ Evidence Fusion     │
                           └──────────┬──────────┘
                                      │
             ┌────────────────────────┼────────────────────────┐
             │                        │                        │
             ▼                        ▼                        ▼
    ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
    │ URL Intelligence│      │ Trusted RAG     │      │ Explainability  │
    │ Offline Analysis│      │ Guidance        │      │ Layer           │
    └─────────────────┘      └─────────────────┘      └─────────────────┘
                                      │
                                      ▼
                           ┌─────────────────────┐
                           │ Risk + Signals +    │
                           │ Recommendations     │
                           └──────────┬──────────┘
                                      │
                                      ▼
                           ┌─────────────────────┐
                           │ Investigation /     │
                           │ Campaign Correlation│
                           └─────────────────────┘


Image Input ──► Tesseract OCR ──► Shared Analysis Pipeline
           └──► OpenCV QR ─────► Offline URL Intelligence

Audio Input ──► FFmpeg ──► whisper.cpp ──► Shared Analysis Pipeline
```

---

## Technology Stack

### Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS

### Backend

- FastAPI
- Python
- Uvicorn

### Machine Learning

- Sentence Transformers
- Multilingual MiniLM
- Logistic Regression
- NumPy
- Scikit-learn

### AI / Semantic Intelligence

- Gemini through an OpenAI-compatible interface
- Structured semantic outputs
- Graceful fallback when unavailable

### OCR and Computer Vision

- Tesseract OCR
- OpenCV
- Pillow

### Speech Processing

- whisper.cpp
- FFmpeg

### Retrieval

- Local multilingual embeddings
- NumPy vector similarity
- Curated trusted cybersecurity guidance

### Deployment

- Vercel
- Next.js frontend
- FastAPI backend

---

## Analysis Pipeline

```text
User Evidence
     │
     ▼
Input Validation
     │
     ├── Text
     ├── URL
     ├── Screenshot
     ├── QR
     └── Audio
     │
     ▼
Evidence Extraction
     │
     ├── OCR
     ├── QR Decode
     ├── Speech-to-Text
     └── URL Parsing
     │
     ▼
Shared Intelligence Pipeline
     │
     ├── Language Detection
     ├── Deterministic Rules
     ├── Local ML
     ├── Optional LLM
     └── Offline URL Intelligence
     │
     ▼
Evidence Fusion
     │
     ├── Risk Level
     ├── Canonical Signals
     ├── Source Agreement
     └── Explanation
     │
     ▼
Trusted Guidance Retrieval
     │
     ▼
User Recommendation
     │
     ▼
Optional Investigation Correlation
```

---

## Canonical Scam Signals

Nazar currently works with a common signal vocabulary:

```text
URGENCY
LINK_REQUEST
IDENTITY_VERIFICATION
BANK_IMPERSONATION
GOVERNMENT_IMPERSONATION
OTP_REQUEST
CREDENTIAL_REQUEST
REMOTE_ACCESS
PAYMENT_REQUEST
ACCOUNT_THREAT
INVESTMENT_PROMISE
```

Using canonical signals allows different intelligence components to communicate through the same representation.

---

## API

### Health

```http
GET /health
```

### Analyze Text

```http
POST /api/analyze/text
```

Example:

```json
{
  "text": "Your bank account will be blocked. Send your OTP immediately."
}
```

### Analyze URL

```http
POST /api/analyze/url
```

Example:

```json
{
  "url": "http://127.0.0.1:8080/login/verify/account"
}
```

### Analyze Screenshot

```http
POST /api/analyze/image
```

Multipart image upload.

### Analyze Audio

```http
POST /api/analyze/audio
```

Multipart audio upload.

### Create Investigation

```http
POST /api/campaigns
```

### Add Investigation Evidence

```http
POST /api/campaigns/{campaign_id}/interactions
```

---

## Production Verification

The deployed Nazar application has been manually smoke-tested end-to-end.

Verified components include:

| Component | Status |
| --- | --- |
| Frontend | Working |
| FastAPI backend | Working |
| Text analysis | Working |
| Deterministic detection | Working |
| Local ML | Working |
| LLM semantic analysis | Working |
| RAG guidance | Working |
| URL analysis | Working |
| Screenshot OCR | Working |
| QR extraction | Working |
| Audio transcription | Working |
| Investigation correlation | Working |

Production tests also verified graceful degradation when the optional LLM layer was temporarily unavailable.

---

## Privacy and Safety Design

Nazar follows a local-first philosophy wherever practical.

OCR, speech transcription, deterministic detection, local ML, URL parsing, and RAG retrieval are designed to operate without sending evidence to external services.

When remote LLM semantic analysis is enabled, text may be transmitted to the configured model provider.

Temporary uploaded media is processed for analysis rather than intentionally retained as a permanent user archive.

Nazar does not automatically access:

- WhatsApp
- SMS
- Banking applications
- Phone calls
- Private accounts

Evidence is explicitly provided by the user.

---

## Current Limitations

Nazar is a research and hackathon prototype, not a production fraud-prevention service.

Current limitations include:

- ML evaluation data is relatively small and partly synthetic.
- Multilingual performance requires further native-language evaluation.
- LLM availability depends on the configured external provider.
- URL analysis is structural and does not currently use live threat-reputation services.
- Screenshot analysis currently focuses on OCR and QR extraction rather than complete visual understanding.
- Speech recognition may contain transcription errors.
- Investigation state is currently temporary rather than a durable user database.
- The trusted-guidance corpus is intentionally small and curated.
- A high risk score indicates suspicious evidence, not confirmed fraud.

Users should independently verify suspicious requests through official channels.

---

## Future Work

Potential extensions include:

- Larger independently reviewed scam datasets
- Stronger Hindi, Tamil, Hinglish, and Tanglish evaluation
- Expanded official-source RAG corpus
- Persistent investigations
- Privacy-preserving redaction before remote AI analysis
- Optional URL threat-intelligence integrations
- Visual phishing and interface analysis
- Campaign-level ML models
- Improved model calibration
- Browser-level end-to-end testing
- Model registry and production observability

---

## Design Philosophy

Nazar is built around three principles.

### Evidence over confidence

A single confidence score should not hide why a system reached its conclusion.

### Local first

Sensitive evidence should remain local whenever the required analysis can reasonably be performed locally.

### Context matters

A suspicious interaction is often only one step in a larger social-engineering sequence.

Nazar therefore analyzes both individual evidence and the relationship between interactions.

---

## Disclaimer

Nazar is an educational and research prototype.

Its output should be treated as decision-support information, not definitive proof that an interaction, person, organization, website, or transaction is fraudulent.

When suspicious activity is detected, users should independently verify the request through an official and trusted communication channel.

---

## Repository

GitHub:

https://github.com/spavan2708/nazar

Live Application:

https://nazar-one-black.vercel.app
