# Nazar

**Nazar** is a multimodal scam-intelligence platform that helps users analyze suspicious messages, links, screenshots, QR codes, and calls before they share sensitive information, open a link, install software, or make a payment.

Unlike conventional scam detectors that analyze each interaction independently, Nazar can connect multiple pieces of evidence and identify how a potential **social-engineering campaign is progressing over time**.

> **One warning before one wrong click.**

### Links

- **Live Deployment:** https://nazar-one-black.vercel.app
- **Repository:** https://github.com/spavan2708/nazar

---

# 1. How Nazar Works

Nazar follows a **Local-First, Multi-Layer Intelligence** architecture.

The central design principle is:

> **No single AI model decides the result. Multiple independent intelligence layers contribute evidence.**

Instead of sending an input to one model and trusting its output, Nazar analyzes evidence through multiple layers:

- Context-aware deterministic detection
- Locally trained machine learning
- Optional LLM semantic analysis
- Trusted-source retrieval
- Modality-specific analysis for URLs, screenshots, QR codes, and audio
- Cross-interaction investigation analysis

These layers contribute evidence to a shared analysis pipeline that produces the final risk assessment, explanation, and recommended action.

## End-to-End Workflow

```text
                         ┌──────────────────────┐
                         │         USER         │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   Evidence Input     │
                         │                      │
                         │ Message / URL        │
                         │ Screenshot / Audio   │
                         └──────────┬───────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 │                  │                  │
                 ▼                  ▼                  ▼
        ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
        │ Deterministic  │ │   Local ML     │ │ Optional LLM   │
        │ Rules Engine   │ │   Classifier   │ │ Semantic Layer │
        └───────┬────────┘ └───────┬────────┘ └───────┬────────┘
                │                  │                  │
                └──────────────────┼──────────────────┘
                                   │
                                   ▼
                         ┌──────────────────────┐
                         │   Evidence Fusion    │
                         └──────────┬───────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 │                  │                  │
                 ▼                  ▼                  ▼
          ┌────────────┐     ┌────────────┐     ┌────────────┐
          │ Risk Score │     │  Signals   │     │Explanation │
          └────────────┘     └────────────┘     └────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Trusted RAG Guidance │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Investigation &      │
                         │ Campaign Correlation │
                         └──────────────────────┘
```

For images and audio, Nazar first extracts usable evidence:

```text
Screenshot ──► Tesseract OCR ──► Text Analysis
           └─► OpenCV QR ──────► URL Analysis

Audio ──────► FFmpeg ──► whisper.cpp ──► Text Analysis
```

---

# 2. Core Philosophy

Nazar is built around four principles.

## 2.1 Evidence Over Blind Confidence

A single confidence score should not hide how a decision was reached.

Nazar exposes the evidence behind its analysis, including:

- Detected scam signals
- Deterministic findings
- ML evidence
- Semantic evidence
- Source agreement
- Relevant trusted guidance

The goal is not simply to say **"this looks suspicious"**, but to explain **why**.

## 2.2 Local First

Sensitive evidence should remain local wherever practical.

Core components such as deterministic detection, ML inference, OCR, QR decoding, speech transcription, URL parsing, and trusted-guidance retrieval are designed to operate within the Nazar backend environment.

Remote semantic AI is an optional additional layer rather than a requirement for the system to function.

## 2.3 Multiple Intelligence Layers

Nazar does not allow one AI model to become the sole source of truth.

Rules, machine learning, semantic analysis, and trusted guidance have different responsibilities and can agree or disagree.

If an optional layer becomes unavailable, Nazar can continue analyzing evidence using the remaining components.

## 2.4 Context Matters

Scams often unfold across several interactions.

A message threatening account suspension may be suspicious on its own. A later message requesting an OTP can reveal a much clearer attack sequence.

Nazar therefore analyzes both **individual evidence** and **the progression across multiple interactions**.

---

# 3. Features

## 3.1 Message Intelligence

Nazar analyzes suspicious text for common social-engineering patterns such as:

- Urgency and pressure
- Bank impersonation
- Government impersonation
- OTP requests
- Credential requests
- Account threats
- Payment requests
- Identity-verification pretexts
- Remote-access requests
- Suspicious links
- Investment promises

The deterministic engine is context-aware.

For example:

```text
Send me the OTP immediately.
```

and:

```text
Never share your OTP with anyone.
```

should not receive the same interpretation.

Nazar attempts to distinguish a malicious request from legitimate safety advice rather than relying only on keyword matching.

---

## 3.2 Screenshot & QR Intelligence

Users can upload suspicious screenshots directly.

Nazar uses **Tesseract OCR** to extract text from screenshots, with support for:

- English
- Hindi
- Tamil

Extracted text is passed through the same intelligence pipeline used for normal messages.

Nazar also uses **OpenCV** to detect QR codes.

If a QR code contains a URL:

```text
Screenshot
     ↓
QR Detection
     ↓
URL Extraction
     ↓
Offline URL Analysis
```

This allows Nazar to inspect the URL structure without automatically opening the destination.

---

## 3.3 Call & Audio Intelligence

Nazar supports uploaded call recordings and other audio evidence.

The pipeline is:

```text
Audio
   ↓
FFmpeg
   ↓
whisper.cpp
   ↓
Transcript
   ↓
Shared Scam Analysis
```

The resulting transcript is analyzed for the same social-engineering signals used by the message pipeline.

The speech model runs locally in the backend environment.

---

## 3.4 URL Intelligence

Nazar performs **offline structural URL analysis**.

It can detect indicators including:

- Non-HTTPS URLs
- Raw IP-address hosts
- Unusual ports
- Embedded credentials
- Login or verification wording
- Credential-heavy paths
- Punycode / IDN indicators
- Mixed-script or lookalike characters
- Deep hostname structures
- URL shorteners
- Long paths
- Complex query strings

Nazar deliberately does not need to visit the suspicious webpage to perform this analysis.

Structural URL analysis is treated as evidence, not proof that a domain is malicious.

---

## 3.5 Cross-Interaction Investigation

This is one of Nazar's central capabilities.

Traditional detectors generally ask:

> **Is this message suspicious?**

Nazar can additionally ask:

> **What is happening across this entire sequence of interactions?**

For example:

```text
Interaction 1
"Your bank account will be blocked."

        ↓

BANK_IMPERSONATION
ACCOUNT_THREAT

        ↓

Interaction 2
"Verify immediately to avoid suspension."

        ↓

URGENCY
IDENTITY_VERIFICATION

        ↓

Interaction 3
"Send the 6-digit OTP you received."

        ↓

OTP_REQUEST

        ↓

Combined Investigation

IMPERSONATION
      ↓
URGENCY_OR_PRESSURE
      ↓
VERIFICATION_PRETEXT
      ↓
AUTHENTICATION_TAKEOVER
```

Nazar can therefore maintain an evolving investigation and show how different pieces of evidence reinforce one another.

Supported attack-stage concepts include:

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

The stages describe patterns supported by the submitted evidence. They do not claim that a real-world compromise definitely occurred.

---

## 3.6 Explainable Intelligence

Nazar exposes the contribution of its intelligence sources instead of hiding everything behind one score.

The analysis can show:

**Deterministic Intelligence**
- Scam signals
- Safety context
- Rule-based evidence

**Machine Learning**
- Classifier output
- Model version
- Evidence level
- Semantically similar examples

**Semantic AI**
- Intent
- Tactics
- Requested actions
- Claimed identity
- Semantic signals

**Trusted Guidance**
- Relevant safety guidance
- Matched topics
- Matched signals
- Source provenance

Nazar can also represent agreement between intelligence sources using states such as:

```text
STRONG_AGREEMENT
PARTIAL_AGREEMENT
RULES_ONLY
ML_ONLY
LLM_ONLY
CONFLICTING
INSUFFICIENT_EVIDENCE
```

This makes disagreement visible rather than hiding it inside an averaged confidence score.

---

# 4. Intelligence Architecture

## 4.1 Deterministic Detection

The deterministic engine provides context-aware detection of known scam and social-engineering patterns.

It produces canonical signals that can be shared across the rest of the system.

Examples include:

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

These signals form a common vocabulary between Nazar's intelligence layers.

---

## 4.2 Machine Learning

Nazar contains a locally trained scam classifier.

The production pipeline is:

```text
Input Message
      ↓
Multilingual MiniLM
      ↓
Sentence Embedding
      ↓
Logistic Regression
      ↓
ML Scam Evidence
```

The sentence encoder is:

```text
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

MiniLM itself is a pretrained multilingual embedding model.

Nazar's **Logistic Regression classifier is trained specifically for scam classification** using the generated embeddings.

The production model can also retrieve semantically similar scam and safe examples to provide additional explainability.

---

## 4.3 Semantic AI

Nazar can optionally use **Gemini** through an OpenAI-compatible interface.

The semantic layer can identify:

- Message intent
- Social-engineering tactics
- Requested actions
- Claimed identity
- Relevant scam signals
- Safety context
- Supporting explanation

The LLM does not independently determine the final result.

If the external provider is unavailable, rate-limited, times out, or returns invalid output, Nazar falls back to its local intelligence layers.

---

## 4.4 Trusted Guidance with RAG

Nazar includes a local **Retrieval-Augmented Generation (RAG)** layer.

The system retrieves relevant scam-prevention guidance from a curated local knowledge base containing information derived from trusted sources such as:

- CERT-In
- State Bank of India
- Delhi Police Cyber Cell

The retrieval flow is:

```text
Detected Evidence
       ↓
Signals / Topics
       ↓
Multilingual Embeddings
       ↓
Local Vector Retrieval
       ↓
Relevant Trusted Guidance
```

Trusted guidance helps the user understand what action to take.

It does **not** artificially increase the scam-risk score.

---

## 4.5 Evidence Fusion

The intelligence layers are combined through explicit evidence-fusion logic.

```text
Deterministic Rules ──┐
                      │
Local ML ─────────────┼──► Evidence Fusion
                      │          │
Semantic AI ──────────┘          │
                                 ▼
                           Risk Assessment
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
                 Signals    Explanation    Action
```

Different detector scores have different meanings and are not blindly averaged together.

This allows Nazar to preserve deterministic evidence while using ML and semantic analysis as additional sources of intelligence.

---

# 5. Machine Learning Evaluation

The current production classifier was evaluated on a frozen benchmark containing:

```text
90 examples
├── 45 scam
└── 45 safe
```

### Results

| Metric | Score |
| --- | ---: |
| Accuracy | **78.9%** |
| Precision | **86.1%** |
| Recall | **68.9%** |
| F1 Score | **76.5%** |
| ROC-AUC | **89.0%** |
| PR-AUC | **90.8%** |

Confusion matrix:

```text
[[40, 5],
 [14, 31]]
```

The production decision threshold is `0.65`.

These metrics come from a **small synthetic and partly translated evaluation dataset** and should not be interpreted as real-world fraud-detection accuracy.

The classifier output is also not presented as a calibrated probability that fraud has occurred.

Nazar has additionally explored multilingual encoder fine-tuning as a research path. Experimental models are kept separate from production when improvements in aggregate performance introduce regressions for particular language groups.

---

# 6. Technology Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js, React |
| Frontend Language | TypeScript |
| Styling | Tailwind CSS |
| Backend | FastAPI, Python |
| API Server | Uvicorn |
| Machine Learning | scikit-learn |
| Embeddings | Multilingual MiniLM |
| Semantic AI | Gemini |
| OCR | Tesseract |
| QR Detection | OpenCV |
| Image Processing | Pillow |
| Speech Recognition | whisper.cpp |
| Audio Processing | FFmpeg |
| Retrieval | MiniLM + NumPy |
| Deployment | Vercel |
| Source Control | GitHub |

---

# 7. Privacy & Safety Architecture

Nazar is designed to analyze evidence submitted by the user.

It does **not** automatically access:

- WhatsApp
- SMS
- Banking applications
- Phone calls
- Private accounts

The user explicitly provides the message, URL, screenshot, or audio evidence to be analyzed.

Most core processing can run inside the Nazar backend environment, including:

- Deterministic detection
- ML inference
- OCR
- QR decoding
- Speech transcription
- URL parsing
- RAG retrieval

When optional remote LLM analysis is enabled, relevant text may be sent to the configured external AI provider.

Environment files and API credentials are excluded from the public repository.

---

# 8. Production Deployment

Nazar is deployed on **Vercel**.

The frontend and backend are deployed from the GitHub repository, while large runtime ML and speech artifacts are stored separately as versioned release assets.

```text
GitHub
   ↓
Vercel Build
   ↓
Download Versioned Runtime Artifacts
   ↓
SHA-256 Verification
   ↓
Restore ML + Speech Models
   ↓
Build Application
   ↓
Production
```

Runtime artifacts are checksum-verified before they are accepted by the build.

This allows the project to remain reproducible without committing hundreds of megabytes of model files directly into normal Git history.

---

# 9. Local Development

## Clone the Repository

```bash
git clone https://github.com/spavan2708/nazar.git
cd nazar
```

## Backend

```bash
cd backend

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The backend runs at:

```text
http://127.0.0.1:8000
```

## Frontend

Open another terminal:

```bash
cd frontend

npm install
npm run dev -- --webpack
```

The frontend runs at:

```text
http://localhost:3000
```

## Environment Variables

Create the required local environment configuration for optional external services.

Example:

```text
GEMINI_API_KEY=your_key_here
```

Never commit real API keys or private environment files to the repository.

---

# 10. Current Limitations

Nazar is a research and hackathon prototype rather than a production fraud-prevention service.

Current limitations include:

- The production ML dataset is relatively small and partly synthetic.
- Multilingual performance requires broader native-language evaluation.
- Screenshot analysis primarily relies on OCR and QR extraction rather than full visual understanding.
- URL intelligence is structural and does not currently use live domain-reputation services.
- Speech recognition may introduce transcription errors.
- Investigation state is currently temporary rather than a persistent authenticated user database.
- The trusted-guidance corpus is intentionally small and curated.
- Optional LLM analysis depends on an external provider.

A high Nazar risk score indicates suspicious evidence detected by the system. It does not establish that fraud has definitely occurred.

---

# 11. Demo

### Live Application

https://nazar-one-black.vercel.app

### GitHub Repository

https://github.com/spavan2708/nazar

---

# Disclaimer

Nazar is an **educational, research, and demonstration project**.

Its analysis should be treated as decision-support information rather than definitive proof that a message, caller, organization, website, or transaction is fraudulent.

When Nazar identifies suspicious behavior, users should independently verify the request using an official communication channel before sharing sensitive information or taking financial action.

---

# Nazar

**One warning before one wrong click.**
