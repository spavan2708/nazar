# Nazar

**Nazar** is a multimodal scam-intelligence platform that helps users analyze suspicious messages, links, screenshots, calls, and digital interactions before they share sensitive information, open a link, install software, or make a payment.

> **One warning before one wrong click.**

Nazar combines deterministic scam detection, locally trained machine learning, optional LLM-based semantic analysis, OCR, speech transcription, URL intelligence, trusted-source retrieval, and cross-interaction investigation analysis.

Rather than treating every suspicious interaction independently, Nazar can connect multiple pieces of evidence and identify how a potential social-engineering campaign is progressing.

---

# 1. How Nazar Works

Nazar follows a **Local-First, Multi-Layer Intelligence** architecture.

The central principle is:

> **No single AI model decides the result. Multiple independent intelligence layers contribute evidence.**

A submitted interaction passes through the relevant extraction layer before entering Nazar's shared analysis pipeline.


User Evidence
    │
    ├── Message
    ├── Link
    ├── Screenshot → OCR
    └── Audio → STT
    │
    ▼
Deterministic Analysis
    │
    ├── Local ML
    └── Optional LLM
    │
    ▼
Risk Fusion
    │
    ▼
Explainable Result
    │
    ▼
Investigation Intelligence
    │
    ▼
Trusted RAG Guidance


The deterministic layer remains available even when optional AI services are unavailable.

---

# 2. Core Capabilities

## Message Analysis

Nazar analyzes suspicious text for social-engineering patterns including:

- OTP and verification-code requests
- Credential requests
- Payment requests
- Bank and government impersonation
- Remote-access requests
- Account threats
- Suspicious links
- Urgency and pressure
- Investment-related scams

The system also considers context and negation.

For example:

```text
"Send me your OTP immediately."
```

and:

```text
"Never send anyone your OTP."
```

should not produce the same analysis.

---

## Multimodal Analysis

Nazar can process multiple forms of evidence:

| Input | Analysis |
|---|---|
| Message | Scam signals, intent and social-engineering patterns |
| Link | Offline structural URL inspection |
| Screenshot | OCR → shared scam-analysis pipeline |
| Audio | Local transcription → shared scam-analysis pipeline |
| QR Code | Safe extraction and inspection of encoded content |

Suspicious URLs are analyzed structurally without automatically opening them.

---

## Investigation Intelligence

Scams often develop over multiple interactions rather than a single message.

Nazar can combine evidence into an investigation and track progression such as:

```text
Impersonation
      ↓
Urgency / Pressure
      ↓
Verification Pretext
      ↓
Link Redirection
      ↓
Credential Harvesting
      ↓
Remote Access
      ↓
Authentication Takeover
      ↓
Payment Extraction
```

This allows Nazar to reason about an evolving interaction instead of evaluating every message in isolation.

Attack stages represent patterns found in the evidence. They do not prove that fraud has occurred.

---

# 3. AI & Machine Learning

Nazar uses a hybrid intelligence architecture rather than relying entirely on generative AI.

## Deterministic Intelligence

A context-aware rule engine identifies canonical scam signals such as:

`URGENCY` · `LINK_REQUEST` · `IDENTITY_VERIFICATION` · `BANK_IMPERSONATION` · `OTP_REQUEST` · `CREDENTIAL_REQUEST` · `REMOTE_ACCESS` · `PAYMENT_REQUEST` · `ACCOUNT_THREAT` · `INVESTMENT_PROMISE`

These rules provide an explainable and reliable fallback.

## Local Machine Learning

Nazar's production semantic classifier uses:

```text
Message
   ↓
Multilingual MiniLM
   ↓
Semantic Embedding
   ↓
Logistic Regression
   ↓
Scam-Risk Classification
```

The MiniLM encoder is pretrained. The Logistic Regression classifier is trained specifically for Nazar.

The current production model was trained on a small balanced research dataset and is supplemented by additional experimental multilingual model research.

Model scores contribute to Nazar's **risk severity** and should not be interpreted as calibrated probabilities of fraud.

## Optional LLM Analysis

An optional LLM provides additional semantic understanding of:

- intent
- requested actions
- claimed identity
- manipulation tactics
- implicit requests
- safety context

The LLM is an enhancement rather than a requirement. If it is unavailable, Nazar continues operating through its deterministic and local ML layers.

---

# 4. Multilingual Intelligence

Nazar is designed around the way suspicious messages are actually written, including informal and mixed-language communication.

Current experimental coverage includes:

- English
- Hindi
- Tamil
- Hinglish
- Tanglish
- Mixed-language messages

The system considers transliteration, spelling variation, informal grammar, indirect requests, and code-switching.

Multilingual robustness remains an active area of development.

---

# 5. Explainability

Nazar is designed to answer not only:

> **How risky does this look?**

but also:

> **Why does it look risky?**

An analysis can expose:

- detected scam signals
- risk severity
- deterministic evidence
- ML contribution
- semantic analysis
- agreement or disagreement between intelligence sources
- investigation stages
- contextual reinforcement
- recommended next actions
- trusted guidance

This keeps model output inspectable rather than presenting a single unexplained AI prediction.

---

# 6. Trusted Guidance

Nazar includes a local retrieval system for trusted cybersecurity guidance.

The guidance layer is deliberately separated from detection:

```text
Detection decides what looks suspicious.
Guidance explains what the user should consider doing next.
```

Retrieved guidance does not modify Nazar's risk score.

---

# 7. Privacy & Safety

Nazar follows a **local-first** design wherever practical.

Core local capabilities include:

- deterministic analysis
- ML classification
- semantic embeddings
- OCR
- speech transcription
- URL structural analysis
- QR decoding
- guidance retrieval
- investigation reasoning

Only optional LLM semantic analysis may require a remote provider.

Nazar does not automatically monitor WhatsApp, SMS, calls, banking activity, or browsing. Users explicitly provide the evidence they want analyzed.

Nazar also does not automatically open suspicious URLs, execute files, submit forms, or perform actions on behalf of the user.

---

# 8. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, React, TypeScript |
| Backend | FastAPI, Python, Pydantic |
| Machine Learning | scikit-learn, Sentence Transformers |
| Embeddings | Multilingual MiniLM |
| Generative AI | Optional LLM provider |
| OCR | Tesseract |
| Speech-to-Text | whisper.cpp, FFmpeg |
| Retrieval | Local embedding-based RAG |
| URL Analysis | Offline structural intelligence |

---

# 9. Local Development

## Clone

```bash
git clone https://github.com/spavan2708/nazar.git
cd nazar
```

## Backend

```bash
cd backend

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## Frontend

In another terminal:

```bash
cd frontend

npm install
npm run dev -- --webpack
```

Open:

```text
http://localhost:3000
```

Some multimodal features additionally require Tesseract, FFmpeg, whisper.cpp, and their associated local model files.

---

# 10. Current Status

Nazar is currently a **research and demonstration system**.

The project already integrates multimodal evidence processing, deterministic scam detection, local machine learning, optional semantic AI, explainability, trusted retrieval, and multi-interaction investigation intelligence.

Current development focuses on stronger real-world datasets, multilingual robustness, persistent investigations, privacy controls, evaluation, model reliability, and production hardening.

Nazar does not claim to prove that fraud has occurred or guarantee that a message, person, payment request, or website is safe.

---

# Nazar

**One warning before one wrong click.**
