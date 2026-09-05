"""Frozen, curated retrieval smoke evaluation; no model fitting or LLM calls."""
import hashlib
import json
from pathlib import Path
from rag.retriever import retrieve_guidance
from services.text_analyzer import analyze_text
from services.investigation_stages import derive_stages


def evaluate():
    root=Path(__file__).resolve().parent
    raw=(root/'v13_retrieval_cases.json').read_bytes()
    cases=json.loads(raw)
    outcomes=[]
    for case in cases:
        analysis=analyze_text(case['text'])
        grounding=retrieve_guidance(case['text'],analysis.signal_codes,derive_stages(analysis))
        if not grounding.available:
            raise RuntimeError('Build/enable the local knowledge index before evaluation')
        expected=set(case['expected_topics'])
        hits={k:set(t for r in grounding.results[:k] for t in r.topics) for k in (1,3)}
        outcomes.append({**case,'signals':sorted(analysis.signal_codes),
            'results':[r.model_dump(mode='json') for r in grounding.results],
            'recall_at_1':len(expected & hits[1])/len(expected) if expected else None,
            'recall_at_3':len(expected & hits[3])/len(expected) if expected else None,
            'topic_match':bool(expected & hits[1]) if expected else not grounding.results})
    positives=[r for r in outcomes if r['expected_topics']]
    metrics={f'Recall@{k}':sum(r[f'recall_at_{k}'] for r in positives)/len(positives) for k in (1,3)}
    metrics['topic_match_accuracy']=sum(r['topic_match'] for r in outcomes)/len(outcomes)
    index=json.loads((root.parent/'rag/index/metadata.json').read_text())
    output={'dataset_sha256':hashlib.sha256(raw).hexdigest(),'knowledge_sha256':index['knowledge_sha256'],
        'embedding_version':index['embedding_version'],'metrics':metrics,'outcomes':outcomes}
    (root/'v13_retrieval_results.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    lines=['# V13 local retrieval evaluation','',
        'Synthetic/curated smoke set: 26 queries, 20 positive-topic queries and 6 benign controls. Authored for V13; not a held-out production benchmark. Existing V3 supplies signals and supported stages. No Gemini call or classifier retraining.', '',
        'Recall@k is mean fraction of expected topics recovered in the first k results, over positive queries. Topic match accuracy counts a relevant first result for positive queries and abstention for benign controls. The two-topic KYC/link case can achieve only 0.5 Recall@1.', '',
        f"Dataset SHA-256: `{output['dataset_sha256']}`.",f"Knowledge SHA-256: `{output['knowledge_sha256']}`.",'',
        *[f'- {key}: {value:.2%}' for key,value in metrics.items()], '',
        '| Query | Expected topics | Retrieved topics (ranked) | Recall@1 | Recall@3 |',
        '|---|---|---|---|---|']
    for row in outcomes:
        found=' → '.join('/'.join(r['topics']) for r in row['results']) or 'abstain'
        one='—' if row['recall_at_1'] is None else f"{row['recall_at_1']:.2f}"
        three='—' if row['recall_at_3'] is None else f"{row['recall_at_3']:.2f}"
        lines.append(f"| {row['id']}: {row['text']} | {', '.join(row['expected_topics']) or 'none'} | {found} | {one} | {three} |")
    findings=root/'v13_retrieval_findings.md'
    if findings.exists(): lines += ['',findings.read_text()]
    (root/'V13_RAG_RETRIEVAL.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(metrics,indent=2))


if __name__=='__main__':
    evaluate()
