# 🛡️ Nazar

> **One warning before one wrong click.**

Nazar is a **multimodal scam-intelligence platform** designed to help users analyze suspicious digital interactions before they click a link, share sensitive information, install software, make a payment, or respond to a potential scam.

Rather than depending on a single AI model, Nazar combines **deterministic security analysis, locally trained machine learning, optional LLM semantic reasoning, OCR, speech-to-text, offline URL intelligence, trusted-source retrieval, explainability, and multi-interaction investigation intelligence**.

The goal of Nazar is not to claim with certainty that something is fraudulent. Instead, it analyzes available evidence, identifies suspicious patterns, explains why they matter, and provides an understandable **risk assessment**.

---

## ✨ What Nazar Can Analyze

Nazar currently supports:

- 💬 **Messages** — suspicious texts, OTP requests, payment requests, impersonation attempts, and social-engineering messages
- 🔗 **Links** — structural analysis of suspicious URLs without automatically opening them
- 🖼️ **Screenshots** — OCR-based extraction and analysis of text inside images
- 🎙️ **Audio / Calls** — local speech transcription followed by scam analysis
- 📱 **QR Codes** — optional extraction of QR content for further inspection
- 🧩 **Investigations** — multiple suspicious interactions combined into one evolving scam timeline

---

# 🧠 Why Nazar Is Different

Most scam detectors analyze one message and return something like:

> Scam / Not Scam

Nazar is designed to go further.

A scam often develops across **multiple interactions**.

For example:

```text
Bank impersonation
        ↓
Account warning
        ↓
Verification request
        ↓
Suspicious link
        ↓
Remote-access request
        ↓
OTP request
        ↓
Payment attempt
```

Nazar can connect evidence across these interactions and show how the suspicious activity may be progressing.

This allows Nazar to operate as a **scam-intelligence and investigation system**, rather than only a message classifier.

---

# 🏗️ System Architecture

```text
                         USER
                          │
                          ▼
                   NAZAR FRONTEND
                          │
          ┌───────────────┼───────────────┐
          │               │               │
       MESSAGE           LINK           MEDIA
                                      ┌────┴────┐
                                  SCREENSHOT   AUDIO
                                      │          │
                                     OCR        STT
                                      │          │
          └───────────────┴───────────┴──────────┘
                          │
                          ▼
                  INPUT NORMALIZATION
                          │
                          ▼
                LANGUAGE DETECTION
                          │
                          ▼
              DETERMINISTIC ANALYSIS
                          │
                          ▼
                   LOCAL ML MODEL
                          │
                          ▼
                 OPTIONAL REMOTE LLM
                          │
                          ▼
                     RISK FUSION
                          │
                          ▼
                EXPLAINABILITY LAYER
                          │
                          ▼
             INVESTIGATION INTELLIGENCE
                          │
                          ▼
                 TRUSTED RAG GUIDANCE
                          │
                          ▼
                   NAZAR RESULT
```

Nazar is intentionally designed so that **optional AI components are not single points of failure**.

If an external LLM becomes unavailable, Nazar can continue operating through its deterministic and local intelligence layers.

---

# 🛠️ Technology Stack

## Frontend

- **Next.js**
- **React**
- **TypeScript**
- **Tailwind CSS**
- Responsive editorial-style interface

## Backend

- **Python**
- **FastAPI**
- **Pydantic**
- **Uvicorn**

## Machine Learning

- **Sentence Transformers**
- **Multilingual MiniLM**
- **Logistic Regression**
- Experimental fine-tuned multilingual transformer models

## LLM

- Optional OpenAI-compatible semantic-analysis provider
- Structured semantic responses
- Confidence-controlled signal integration
- Retry and fallback handling
- Prompt-injection-aware input separation

## OCR

- **Tesseract OCR**
- English
- Hindi
- Tamil

## Speech-to-Text

- **whisper.cpp**
- Local multilingual Whisper model
- FFmpeg preprocessing

## Retrieval-Augmented Generation

- Local multilingual embeddings
- Local vector retrieval
- Curated cybersecurity guidance
- Source provenance

## URL Intelligence

- Offline structural URL inspection
- No automatic browsing of suspicious websites

---

# 🤖 AI & Machine Learning

Nazar uses several different forms of artificial intelligence.

It is important to distinguish between models **trained by Nazar** and pretrained systems that Nazar uses as components.

---

## Production Scam Classifier

The current production semantic classifier uses:

```text
Message
   ↓
paraphrase-multilingual-MiniLM-L12-v2
   ↓
384-dimensional semantic embedding
   ↓
Logistic Regression
   ↓
Scam-risk prediction
```

### Model Details

| Property | Value |
|---|---|
| Classifier | Logistic Regression |
| Embedding Model | `paraphrase-multilingual-MiniLM-L12-v2` |
| Embedding Dimension | 384 |
| Production Training Examples | 150 |
| Scam Training Examples | 75 |
| Safe Training Examples | 75 |
| Evaluation Examples | 90 |
| Evaluation Scam Examples | 45 |
| Evaluation Safe Examples | 45 |
| Decision Threshold | 0.65 |

### Recorded Production Evaluation

| Metric | Result |
|---|---:|
| Accuracy | **78.89%** |
| Precision | **86.11%** |
| Recall | **68.89%** |
| F1 Score | **76.54%** |
| ROC-AUC | **88.99%** |
| PR-AUC | **90.81%** |

Confusion matrix:

```text
[[40, 5],
 [14, 31]]
```

These metrics come from a **small, synthetic, balanced evaluation dataset**.

They should **not** be interpreted as real-world fraud-detection accuracy.

The model's output is also **not a calibrated probability that fraud is occurring**.

---

# 🧪 Research Models

Nazar contains additional machine-learning research that is **not automatically deployed to production**.

Experiments include:

- Logistic Regression variants
- Class-weighted Logistic Regression
- Calibrated classifiers
- Linear SVM
- MLP classifiers
- Fine-tuned multilingual transformer encoders
- Multilingual recovery experiments
- Signal-specific classifier experiments

One experimental fine-tuned multilingual encoder recorded approximately:

| Metric | Result |
|---|---:|
| Accuracy | **85.88%** |
| Precision | **90.91%** |
| Recall | **76.92%** |
| F1 Score | **83.33%** |

This remains a **research model**, not the current production model.

Nazar does not promote a model simply because its overall accuracy is higher.

A candidate must also be evaluated for:

- multilingual robustness
- safety false positives
- scam recall
- implicit requests
- adversarial behavior
- latency
- reproducibility
- subgroup regressions

---

# 🧠 What Nazar Actually Trained

Nazar has trained:

- v1 Logistic Regression scam classifier
- v2 Logistic Regression scam classifier
- experimental classifier candidates
- experimental fine-tuned multilingual encoder models

Nazar did **not train from scratch**:

- MiniLM
- Whisper
- Tesseract
- the optional remote LLM

These are pretrained systems used as components.

This distinction is intentional so that the project's AI claims remain technically accurate.

---

# ⚙️ Deterministic Scam Intelligence

Machine learning is not Nazar's only defense.

Nazar contains a deterministic context-aware analysis engine that searches for suspicious requests and social-engineering patterns.

It can identify concepts such as:

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

These canonical signals are shared across Nazar's different analysis systems.

---

# 🛡️ Safety Context

Nazar attempts to distinguish between a malicious request and advice warning someone about that request.

For example:

```text
Send me your OTP immediately.
```

is fundamentally different from:

```text
Never send anyone your OTP.
```

The deterministic engine therefore considers:

- request intent
- sensitive objects
- urgency
- pressure
- negation
- safety language
- impersonation
- contextual combinations

This helps reduce false positives from legitimate cybersecurity advice.

---

# 🎯 Risk Scoring

Nazar produces a **risk severity score from 0–100**.

Current risk levels are:

```text
0–29      LOW
30–64     MEDIUM
65–84     HIGH
85–100    CRITICAL
```

The Nazar score represents **risk severity inside Nazar's analysis system**.

It does NOT mean:

```text
80 score = 80% probability of fraud
```

Nazar does not currently provide calibrated real-world fraud probabilities.

---

# 🔀 Risk Fusion

Nazar does not simply average every model.

The deterministic engine remains the foundation.

Additional intelligence sources may increase the severity when enough independent evidence exists.

Conceptually:

```text
                 DETERMINISTIC SCORE
                         │
              ┌──────────┴──────────┐
              │                     │
         LOCAL ML                LLM AI
              │                     │
              └──────────┬──────────┘
                         │
                    RISK FUSION
                         │
                         ▼
                  FINAL RISK SCORE
```

Optional ML or LLM components are not allowed to silently erase strong deterministic findings.

---

# 🧩 Explainable AI

Nazar attempts to explain **how it reached a result**, rather than showing only a score.

Depending on which systems are available, results may include:

- deterministic evidence
- detected signals
- ML score
- model version
- semantic evidence
- similar semantic examples
- LLM reasoning
- source agreement
- source disagreement
- trusted cybersecurity guidance
- investigation stages
- contextual reinforcement

Possible agreement states include:

```text
STRONG_AGREEMENT
PARTIAL_AGREEMENT
ML_ONLY
RULES_ONLY
LLM_ONLY
CONFLICTING
INSUFFICIENT_EVIDENCE
```

Agreement describes consistency between Nazar's intelligence sources.

It does not prove that the conclusion is objectively correct.

---

# 🌍 Multilingual Scam Detection

Nazar is designed for multilingual digital communication.

Current language coverage includes:

- 🇬🇧 English
- 🇮🇳 Hindi
- 🇮🇳 Tamil
- Hinglish
- Tanglish
- Mixed-language messages

This matters because real scam messages often look like:

```text
Sir code aya hoga phone pe woh 6 digit wala bhej do jaldi
verification expire ho jayega
```

rather than perfectly written formal text.

Nazar therefore includes support for:

- transliteration
- mixed languages
- informal grammar
- spelling variations
- implicit sensitive requests

Multilingual support is still an active research area in Nazar and should not be interpreted as complete coverage of Indian languages.

---

# 🔗 URL Intelligence

Nazar can inspect suspicious URLs **without automatically opening them**.

Structural indicators can include:

- insecure HTTP
- IP-address hosts
- unusual ports
- embedded credentials
- punycode
- internationalized domains
- mixed-script domains
- lookalike characters
- shortened links
- suspicious login wording
- verification wording
- deep hostnames
- long paths
- complex query strings

Example pipeline:

```text
URL
 ↓
Normalization
 ↓
Structural Inspection
 ↓
Risk Indicators
 ↓
Structural Risk
 ↓
Nazar Analysis
```

Nazar currently does **not** automatically:

- browse the page
- execute JavaScript
- follow redirects
- query live reputation services
- perform DNS threat analysis
- guarantee that a URL is safe

---

# 🖼️ Screenshot Analysis

Nazar can analyze suspicious screenshots.

Supported image formats include:

```text
PNG
JPEG
WEBP
```

The screenshot pipeline is primarily:

```text
Screenshot
    ↓
Image Validation
    ↓
Tesseract OCR
    ↓
Extracted Text
    ↓
Nazar Scam Intelligence
```

Current protections include:

- upload-size limits
- MIME validation
- image-format validation
- image-dimension limits
- animated-image rejection

Optional QR extraction may also be used when available.

Nazar currently does not claim reliable visual brand verification or sender-identity verification.

---

# 📱 QR Intelligence

Where supported, Nazar can extract QR content from screenshots.

Decoded content can then be inspected rather than automatically executed.

This allows QR-based links or payment information to become part of the same evidence-analysis pipeline.

Nazar never automatically opens a URL simply because it was found inside a QR code.

---

# 🎙️ Audio & Call Analysis

Nazar can analyze suspicious audio recordings.

Supported formats include:

```text
WAV
MP3
M4A
WEBM
```

Pipeline:

```text
Audio
  ↓
Validation
  ↓
FFmpeg
  ↓
16 kHz Mono Audio
  ↓
whisper.cpp
  ↓
Transcript
  ↓
Nazar Scam Analysis
```

Speech transcription is performed locally using a pretrained Whisper model.

Temporary audio processing files are removed after analysis.

The resulting transcript can then be analyzed using the same intelligence pipeline as a text message.

---

# 📚 Trusted Guidance — RAG

Nazar includes a local Retrieval-Augmented Generation / retrieval system for trusted cybersecurity guidance.

The purpose of RAG is to answer:

> **What should the user do next?**

rather than:

> **Is this definitely a scam?**

Guidance can cover topics such as:

- OTP safety
- credentials
- remote-access software
- banking / KYC
- phishing
- UPI payments
- account threats
- government impersonation
- investment scams
- recovery scams

The RAG system is deliberately isolated from the risk score.

```text
RAG can provide guidance.

RAG cannot increase or decrease Nazar's risk score.
```

This separation prevents retrieved documents from accidentally manipulating the core detection system.

---

# 🔍 Investigation Intelligence

One of Nazar's main differentiators is the ability to combine several suspicious interactions.

An investigation may contain:

- messages
- links
- screenshots
- calls/audio

Each piece of evidence contributes to an evolving timeline.

Nazar tracks:

- individual evidence risk
- combined signals
- attack stages
- stage progression
- contextual reinforcement
- campaign-level risk
- evidence history

---

# 🧭 Attack Progression

Current investigation stages include:

```text
IMPERSONATION
        ↓
URGENCY_OR_PRESSURE
        ↓
VERIFICATION_PRETEXT
        ↓
LINK_REDIRECTION
        ↓
CREDENTIAL_HARVESTING
        ↓
REMOTE_ACCESS
        ↓
AUTHENTICATION_TAKEOVER
        ↓
PAYMENT_EXTRACTION
```

Nazar also supports:

```text
INVESTMENT_LURE
```

Not every investigation follows the same order.

Stages describe patterns observed in the evidence.

They do not prove that an attack has succeeded.

---

# 🔗 Contextual Reinforcement

Individual messages may appear harmless when viewed alone.

For example:

```text
Message 1:
"Your bank account needs verification."

Message 2:
"Install this support application."

Message 3:
"Tell me the six-digit number that appeared."
```

The third message becomes more meaningful when Nazar considers the earlier evidence.

Nazar therefore supports **contextual reinforcement** between related evidence while keeping inherited context distinguishable from directly detected signals.

---

# 🤖 Optional LLM Semantic Analysis

Nazar can use an optional remote LLM to provide additional semantic analysis.

The LLM may analyze:

- intent
- requested actions
- claimed identity
- manipulation tactics
- suspicious signals
- safety-warning context
- semantic explanation

The provider is optional.

If the provider is:

- disabled
- unavailable
- rate-limited
- timed out
- incorrectly configured
- returning malformed output

Nazar continues using its local intelligence systems.

The LLM is therefore an **enhancement**, not the foundation of Nazar.

---

# 🔐 Prompt Injection Protection

User messages are treated as **untrusted data**.

They are separated from Nazar's system instructions and passed through structured semantic-analysis boundaries.

The system does not intentionally treat instructions inside a suspicious message as commands for Nazar itself.

---

# 🏠 Local-First Architecture

A major design principle behind Nazar is keeping sensitive processing local whenever practical.

### Local

- deterministic analysis
- ML classifier
- MiniLM embeddings
- OCR
- speech transcription
- URL structural analysis
- QR decoding
- RAG retrieval
- investigation reasoning

### Potentially Remote

- optional LLM semantic analysis

This means Nazar can continue providing meaningful analysis even without access to an external LLM.

---

# 🔒 Privacy

Nazar does not automatically monitor:

- WhatsApp
- SMS
- email
- bank accounts
- phone calls
- browsing activity

Users explicitly submit evidence for analysis.

Local processing is used wherever practical.

When optional remote LLM analysis is enabled, submitted text may be sent to the configured AI provider for semantic processing.

Improved privacy controls and redaction are part of Nazar's continued development.

---

# 🧪 Testing

Nazar contains extensive backend tests covering areas such as:

- deterministic analysis
- canonical signals
- safety context
- implicit requests
- multilingual inputs
- machine learning
- LLM fallback
- OCR
- audio
- URLs
- QR handling
- RAG
- investigations
- attack stages
- contextual reinforcement
- validation
- malformed input
- resource limits

At the most recent repository audit:

```text
215 backend tests passed
1 optional test skipped
```

Frontend validation includes:

- ESLint
- production Webpack build
- static UI checks
- accessibility-oriented checks
- upload validation checks
- safe-link rendering checks

---

# 📂 Project Structure

```text
nazar/
│
├── backend/
│   │
│   ├── main.py
│   ├── services/
│   ├── schemas/
│   ├── tests/
│   │
│   ├── ml/
│   │   ├── data/
│   │   ├── artifacts/
│   │   ├── training/
│   │   └── research/
│   │
│   ├── rag/
│   │   ├── knowledge/
│   │   └── index/
│   │
│   ├── evaluation/
│   └── stt/
│
├── frontend/
│   ├── app/
│   ├── public/
│   └── scripts/
│
├── DESIGN.md
├── .gitignore
└── README.md
```

---

# 🚀 Running Nazar Locally

## 1. Clone the Repository

```bash
git clone https://github.com/spavan2708/nazar.git
cd nazar
```

---

## 2. Start the Backend

```bash
cd backend

python -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Backend:

```text
http://127.0.0.1:8000
```

---

## 3. Start the Frontend

Open another terminal:

```bash
cd frontend

npm install

npm run dev -- --webpack
```

Frontend:

```text
http://localhost:3000
```

---

# ⚙️ Optional System Dependencies

Some Nazar capabilities require additional local dependencies.

## Tesseract OCR

For macOS:

```bash
brew install tesseract tesseract-lang
```

---

## FFmpeg

```bash
brew install ffmpeg
```

---

## whisper.cpp

```bash
brew install whisper-cpp
```

Large model files are intentionally not committed to the repository.

---

# 🔑 Environment Configuration

Create:

```text
backend/.env
```

using the provided:

```text
backend/.env.example
```

Configuration may include variables such as:

```text
LLM_ENABLED
LLM_API_KEY
LLM_MODEL
LLM_BASE_URL
LLM_TIMEOUT_SECONDS

OCR_LANGUAGES

QR_ENABLED
```

**Never commit `.env` or API keys to GitHub.**

---

# ⚠️ What Nazar Does NOT Claim

Nazar does not claim that it can:

- identify a scammer with certainty
- prove that fraud occurred
- guarantee that a website is safe
- verify the identity of a bank employee
- verify government officials
- automatically monitor WhatsApp
- automatically monitor calls
- inspect bank accounts
- understand every Indian language perfectly
- provide calibrated fraud probabilities
- replace banks, law enforcement, or cybersecurity authorities

Nazar is a **risk-analysis and digital-safety intelligence system**.

---

# 🚧 Current Limitations

Nazar is still a research-oriented project.

Important limitations include:

- relatively small production ML dataset
- synthetic-heavy training and evaluation data
- limited independently labeled real-world examples
- uneven multilingual coverage
- incomplete native-speaker validation
- imperfect indirect-request detection
- limited real-world OCR benchmarking
- limited real-world speech benchmarking
- small trusted-guidance corpus
- structural-only URL analysis
- optional dependency on a remote LLM
- limited production observability
- investigation persistence and identity controls still evolving

These limitations are intentionally documented rather than hidden.

---

# 🗺️ Roadmap

Current engineering priorities include:

- larger and more realistic training datasets
- stronger multilingual datasets
- native-speaker review
- improved local ML
- multi-task scam and signal classification
- stronger safety/negation modeling
- persistent investigations
- user/session isolation
- privacy controls
- remote-AI redaction
- rate limiting
- canonical model release gates
- model artifact registry
- expanded trusted cybersecurity guidance
- hybrid RAG retrieval
- stronger screenshot intelligence
- improved QR intelligence
- optional threat-intelligence integrations
- campaign-level evaluation
- campaign reasoning research
- browser-level E2E testing
- production observability
- reproducible deployment

---

# 💡 Engineering Philosophy

Nazar is built around a few important principles.

### 1. AI is evidence, not authority

A model prediction should contribute evidence rather than become unquestionable truth.

### 2. Deterministic fallback

The application should remain useful even when optional AI services fail.

### 3. Explain before claiming

Users should understand why Nazar considers something suspicious.

### 4. Local where possible

Sensitive processing should remain local whenever practical.

### 5. Never automatically trust suspicious content

Nazar does not automatically open suspicious links, execute files, submit forms, or perform payments.

### 6. Honest evaluation

Synthetic benchmarks are labeled synthetic.

Research models are labeled research.

Pretrained models are not described as models trained by Nazar.

---

# 📌 Project Status

Nazar is currently best described as:

> **A local-first multimodal scam-intelligence platform combining deterministic reasoning, locally trained machine learning, optional LLM semantic analysis, OCR, speech transcription, offline URL intelligence, trusted-source retrieval, explainability, and multi-interaction scam investigation.**

Nazar is currently a **research and demonstration system** and should not yet be treated as a production fraud-verification service.

---

# ⚖️ Disclaimer

Nazar provides automated digital-safety analysis for educational and assistive purposes.

Its results may contain **false positives and false negatives**.

A low-risk result does not guarantee that a message, person, payment request, QR code, or website is safe.

A high-risk result does not prove that fraud has occurred.

For suspected cybercrime or financial fraud, independently verify the situation through official channels and contact the appropriate financial institution or authorities when necessary.

---

<div align="center">

# 🛡️ NAZAR

### One warning before one wrong click.

**Multimodal Scam Intelligence · Local ML · Explainable AI · Investigation Correlation**

</div>
