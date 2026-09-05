<div align="center">

# 🛡️ NAZAR

### One warning before one wrong click.

**AI-powered multimodal scam intelligence that looks beyond a single suspicious message.**

</div>

---

## 👁️ What is Nazar?

**Nazar** is a multimodal digital-safety platform that helps users analyze suspicious **messages, links, screenshots, calls, and QR codes** before they click, share sensitive information, install software, or make a payment.

Instead of depending on a single AI model, Nazar combines:

- 🧠 **Local Machine Learning**
- 🤖 **Optional LLM Semantic Analysis**
- 🛡️ **Deterministic Scam Detection**
- 🖼️ **OCR Screenshot Analysis**
- 🎙️ **Speech-to-Text Call Analysis**
- 🔗 **Offline URL Intelligence**
- 📚 **Trusted RAG Guidance**
- 🧩 **Multi-interaction Scam Investigations**

---

## ✨ The Idea

Scams rarely happen in just one message.

A conversation might evolve like this:

```text
Bank impersonation
        ↓
Account warning
        ↓
"Verify your identity"
        ↓
Suspicious link
        ↓
Remote-access request
        ↓
"Send me the OTP"
```

Most scam detectors analyze each interaction independently.

**Nazar connects the evidence.**

It tracks suspicious signals and attack stages across multiple interactions to help reveal an evolving social-engineering campaign.

---

## 🔍 What Can Nazar Analyze?

| Input | Nazar does |
|---|---|
| 💬 Message | Detects suspicious requests, impersonation and social engineering |
| 🔗 Link | Inspects structural phishing indicators without opening the site |
| 🖼️ Screenshot | Extracts text with OCR and analyzes the conversation |
| 🎙️ Call / Audio | Transcribes speech locally and analyzes the transcript |
| 📱 QR Code | Extracts suspicious QR content safely |
| 🧩 Investigation | Connects multiple pieces of evidence into one timeline |

---

## 🧠 How It Works

```text
        Message / Link / Screenshot / Audio
                       │
                       ▼
              Evidence Extraction
                       │
                       ▼
        Deterministic Scam Intelligence
                       │
              ┌────────┴────────┐
              ▼                 ▼
          Local ML        Optional LLM
              └────────┬────────┘
                       ▼
                  Risk Fusion
                       │
                       ▼
           Investigation Intelligence
                       │
                       ▼
          Explainable Risk Assessment
                       │
                       ▼
             Trusted RAG Guidance
```

Nazar is designed with a **local-first fallback** — core analysis can continue even when the optional remote LLM is unavailable.

---

## 🚨 What Nazar Looks For

Nazar can identify patterns including:

`OTP Requests` · `Credential Theft` · `Bank Impersonation` · `Government Impersonation` · `Remote Access` · `Payment Requests` · `Suspicious Links` · `Account Threats` · `Urgency` · `Investment Scams`

It also considers **context and negation**.

```text
❌ "Send me your OTP immediately."

✅ "Never send anyone your OTP."
```

Those should not receive the same analysis.

---

## 🌍 Built for Real Conversations

Nazar is designed to handle more than perfectly written English.

Current experimental multilingual support includes:

**English · Hindi · Tamil · Hinglish · Tanglish · Mixed-language messages**

For example:

```text
sir code aya hoga phone pe woh 6 digit wala
bhej do jaldi verification expire ho jayega
```

---

## 🧩 Investigation Intelligence

This is one of Nazar's core features.

Multiple suspicious interactions can be grouped into a single investigation, allowing Nazar to track progression such as:

```text
IMPERSONATION
      ↓
URGENCY
      ↓
VERIFICATION PRETEXT
      ↓
LINK REDIRECTION
      ↓
REMOTE ACCESS
      ↓
AUTHENTICATION TAKEOVER
      ↓
PAYMENT EXTRACTION
```

This turns Nazar from a simple **scam classifier** into a **scam-intelligence system**.

---

## ⚙️ Tech Stack

**Frontend:** Next.js · React · TypeScript · Tailwind CSS

**Backend:** Python · FastAPI · Pydantic

**AI/ML:** Sentence Transformers · Multilingual MiniLM · Logistic Regression · Optional LLM

**Multimodal:** Tesseract OCR · whisper.cpp · FFmpeg · QR Analysis

**Intelligence:** Local RAG · URL Analysis · Investigation Correlation · Explainable Risk Fusion

---

## 🚀 Run Locally

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev -- --webpack
```

Open:

```text
http://localhost:3000
```

Some multimodal features additionally require **Tesseract, FFmpeg, and whisper.cpp**.

---

## 🔐 Privacy by Design

Nazar does **not** automatically monitor WhatsApp, calls, banking activity, or browsing.

Users choose what evidence to analyze.

OCR, speech transcription, ML classification, URL inspection, and RAG can operate locally. Remote LLM analysis is an **optional enhancement**, not a requirement.

---

## ⚠️ Current Status

Nazar is currently a **research and demonstration system**, not a production fraud-verification service.

Its risk score represents **risk severity, not the probability that fraud occurred**, and results may contain false positives or false negatives.

---

<div align="center">

## 🛡️ Think before you trust.

### **Nazar — One warning before one wrong click.**

</div>
