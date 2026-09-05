# V13 curated source provenance

Reviewed 2026-09-05. `guidance.json` contains ten manually paraphrased safety items, not copied articles or user evidence. Each short item is one local document and currently one chunk. Source URLs are citations only; build and retrieval do not visit them.

| Local items | Official publication | Section / date evidence |
|---|---|---|
| otp-safety, remote-access-safety | [State Bank of India contact centre](https://sbi.co.in/web/customer-care/contact-centre) | Customer security text prohibits OTP sharing and downloading third-party applications at a purported SBI representative's request. Publication/update date not established; stored as null. |
| password-safety, phishing-safety, upi-safety, account-threat-safety | [CERT-In Cyber Security Awareness Booklet](https://www.cert-in.org.in/PDF/CSA_Booklet.pdf) | October 2023 stated in the booklet; printed pages 4, 5, 14. Short paraphrases of phishing, account-deactivation pretexts, OTP/UPI receiving-money precautions and password privacy. |
| banking-kyc-safety | [Delhi Police Cyber Cell: Financial App KYC Frauds](https://cyber.delhipolice.gov.in/Appkyc.html) | Modus operandi and precautions. Publication/update date not established; stored as null. |
| government-impersonation-safety | [I4C/NCTAU Digital Arrest advisory](https://cybercrime.gov.in/pdf/Advisories/ADVISORYTAU-ADV-003DigitalArrest06.03.2025.pdf) | Advisory TAU/ADV/003 dated 6 March 2025, pages 1–2. |
| investment-safety | [CERT-In Digital Safety Compass Handbook, hosted by Cyber Swachhta Kendra](https://www.csk.gov.in/documents/CERT-In_Digital_Safety_Compass_Handbook.pdf) | Safer Internet Day, February 2025; Fake Trading Apps, printed page 17. Reviewed official indexed excerpt; direct PDF fetch timed out during curation. |
| recovery-safety | [US FTC: Refund and Recovery Scams](https://consumer.ftc.gov/articles/refund-and-recovery-scams) | General unsolicited recovery-offer precautions. US government source is explicitly labelled; no US legal entitlement or reporting procedure is imported. Publication/update date not established; stored as null. |

The primary source set is Indian government and official Indian bank guidance. The recovery topic uses an explicitly identified US government consumer-protection source within the government cyber-safety source family. RBI documents were considered but direct copies could not be fetched reliably; no unverified RBI attribution is included.

Paraphrases are not official quotations or endorsements of Nazar. Dates are publication dates only when established, never inferred from a search crawl date. Review date is recorded separately. Link hosts are explicitly allowlisted in backend and frontend. Adding a host requires code review, not a runtime user setting. A hostname check is not a substitute for reviewing a specific publication and its claims.

Maintenance: review the actual page, write a concise paraphrase, record section and date/provenance, validate topic/signal tags, run `python -m rag.build_index`, run tests/evaluation, and restart the backend when replacing the local embedding model. Do not ingest arbitrary pages, scraped feeds, uploaded evidence, prompts, credentials, or personal data. No online updates are scheduled. Future source changes require a new manual review; local guidance can become stale.
