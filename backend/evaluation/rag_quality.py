"""JSON-only source hygiene and frozen retrieval evaluation."""
import argparse,json
from datetime import date
from pathlib import Path
from rag.knowledge import load_documents,chunk_documents
from rag.retriever import retrieve_guidance
from services.text_analyzer import analyze_text
from services.investigation_stages import derive_stages


def run():
    docs,_=load_documents();cases=json.loads((Path(__file__).parent/'v13_retrieval_cases.json').read_text());rows=[]
    for case in cases:
        rule=analyze_text(case['text']);result=retrieve_guidance(case['text'],rule.signal_codes,derive_stages(rule))
        expected=set(case['expected_topics']);found={t for r in result.results for t in r.topics}
        rows.append(dict(id=case['id'],expected_topics=sorted(expected),retrieved_topics=sorted(found),available=result.available,
            recall=len(expected&found)/len(expected) if expected else None,benign_abstained=not result.results if not expected else None,
            result=result.model_dump(mode='json')))
    positive=[r['recall'] for r in rows if r['recall'] is not None]
    return dict(documents=len(docs),chunks=len(chunk_documents(docs)),sources=[dict(id=d.id,source=d.source_name,reviewed_on=str(d.reviewed_on),review_due=(date.today()-d.reviewed_on).days>180) for d in docs],
        cases=rows,mean_topic_recall=sum(positive)/len(positive),benign_controls=sum(r['benign_abstained'] is not None for r in rows),
        benign_abstentions=sum(r['benign_abstained'] is True for r in rows),risk_effect='none',
        limitations='Frozen synthetic smoke set; source freshness uses review age, not live website verification. No threshold tuned on this set.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    with a.output.open('x') as f: f.write(json.dumps(run(),indent=2)+'\n')
