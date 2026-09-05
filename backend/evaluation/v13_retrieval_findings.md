## Manual failure inspection

The ranking and gates were fixed before running this set; no V4 model changes or threshold tuning were performed in response to these results. Scores here are cosine retrieval similarities, not scam probabilities.

- **rag-001 (OTP paraphrase):** V3 emits both CREDENTIAL_REQUEST and OTP_REQUEST. Password guidance has similarity 0.497 versus 0.154 for OTP guidance, so both qualify through signals but credentials rank first. OTP is recovered at rank 2. Topic overlap makes single-topic Recall@1 strict here; credential guidance is related but less specific.
- **rag-010 (phishing):** V3 emits no canonical signal for this wording. The phishing topic cue exists, but similarity 0.234 is below the 0.25 topic gate. The retriever abstains. This is a real coverage loss near the conservative gate.
- **rag-014 (investment):** V3 emits no investment signal. The correct reference is nearest at 0.244, just below the 0.25 gate. It abstains despite a relevant topic cue. This smoke set does not justify lowering a general gate.
- **rag-016 (Hindi OTP):** No V3 signal is emitted. The Hindi topic cue matches, but OTP guidance similarity is only 0.012. English-only reference text and multilingual representation limitations plausibly contribute; this observation does not establish language-wide performance.
- **rag-018 (Tamil credentials):** No V3 signal is emitted. The Tamil password cue matches, but password guidance similarity is 0.033. Unrelated phishing guidance is nearest at 0.237 and is correctly not returned. The model and current reference language do not reliably bridge this query.
- **rag-019 (indirect remote access):** No canonical signal or explicit topic cue supports the euphemism. The relevant reference is nearest at 0.183 but far below the semantic-only gate of 0.72, so it abstains.
- **rag-020 (indirect recovery):** “Retrieve the stolen savings” is not covered by the curated recovery cue. The correct reference is nearest at 0.464, above the topic gate but below the semantic-only gate. With no independent topic/signal match, it abstains.

All six benign controls abstain. That is a useful smoke check, not evidence of a production false-positive rate. The one KYC/phishing multi-topic query recovers both topics within three results. Safety-warning guidance is returned as topic context without treating that context as detector evidence.

## Scope and reproducibility

The set is small, synthetic, and authored in the same development task as the retriever. It is not an independent held-out benchmark. It overrepresents explicit English wording and includes only a few multilingual probes. Recall can be reduced by one-result-per-publication deduplication when multiple relevant topics share a source URL. Investigation summaries deliberately use canonical signals/stages only, and therefore cannot recover topic-only context from earlier safety warnings.

Re-run from backend: `PYTHONPATH=. .venv/bin/python evaluation/evaluate_v13.py` after `python -m rag.build_index`. Detailed per-query results, similarities, source IDs, signals, dataset hash and embedding fingerprint are in `v13_retrieval_results.json`. Knowledge text remains separate from the evaluation queries.
