## Interpretation and limitations

These are hypotheses from the frozen errors and semantic neighborhoods, not demonstrated causes. No ablation, retraining, or new provider call was performed.

### Five false positives

- eval-056: Tamil safety negation is missed by V3. Suspicious and safe references both exceed 0.98 similarity. This suggests weak semantic separation in these local embeddings; similarity cannot distinguish the opposing instructions reliably.
- eval-057: Tamil test-server context is also extremely close to both classes. Hard-negative diversity and likely embedding limitations merit investigation; a nearest suspicious reference does not establish malicious intent.
- eval-069: An educational investment warning scores 0.887. Investment scam neighbors (0.529 / 0.440) outrank safe references (0.293 / 0.277). This is consistent with topic overlap overwhelming negation and insufficient Hinglish warning diversity.
- eval-076: The nearest safe warning (0.762) is closer than either suspicious neighbor (0.627 / 0.593), yet the classifier scores 0.783. The linear classifier uses the whole embedding, not nearest-neighbor voting. Tanglish negation and safety-warning overlap remain weaknesses.
- eval-080: Advice to independently verify a court/voucher claim overlaps both labels (0.437 suspicious / 0.419 safe). V3 also emits IDENTITY_VERIFICATION. Ambiguous verification language and training diversity are plausible factors.

V3 does not recognize safety-warning context in any of these five cases. With V5 unavailable, four produce ML_ONLY and eval-080 produces PARTIAL_AGREEMENT, not CONFLICTING. Agreement can only expose safety context actually detected; it cannot repair missing language coverage. A true safety label in the benchmark is not an input to production agreement.

### Representative false negatives

- eval-003 / eval-004: “one-time login secret” and “mailbox passphrase” expose euphemistic credential coverage gaps. Reference similarities are modest and the low scores suggest insufficient paraphrase diversity.
- eval-043: Hindi tax-officer coercion has a related suspicious reference (0.579), yet scores 0.202. Government-pretext diversity and multilingual representation are plausible limitations.
- eval-062 / eval-082: Hinglish and mixed-language remote-access requests overlap legitimate support/safety references. The former is slightly closer to safe examples; the latter is closer to suspicious examples but still below threshold. Wording ambiguity, language coverage, and linear decision-boundary limitations are plausible.
- eval-075: Tanglish investment semantics have weak similarities across both labels (maximum 0.379). Training coverage and language representation deserve investigation.
- eval-011: Parcel disposal/payment wording has only moderate related references. This suggests missing scenario diversity; structural URL analysis was not included in the V3-only signal inspection here.
- eval-012: OCR substitutions resemble an OCR safety warning more closely than a suspicious request. Corruption and safety-language overlap plausibly obscure direction of intent.
- eval-017: Emergency-relative payment coercion lacks a close matching scenario; insufficient training diversity is a plausible contributor.
- eval-007: A related government-voucher scam is the nearest reference, but score 0.617 misses 0.65. Semantic proximity alone does not determine the classifier boundary.

The selected ten cover five languages and eight categories; there are no Tamil false negatives in the saved list. This is a qualitative sample, not a new performance estimate. High Tamil similarity is suggestive of representation limitations, not proof of their cause. The small curated dataset cannot establish real-world calibration or language-wide accuracy.
