"""Explicitly bounded provider variance evaluation; no calls unless --live is set."""
import argparse,json
from pathlib import Path
from services.llm.semantic_analyzer import analyze_semantics

CASES=(
    ('safety','Never share authentication numbers with callers.'),
    ('credential','Send your online banking password to this chat.'),
    ('benign','The library will reopen on Monday morning.'),
    ('hindi','ओटीपी किसी को मत बताइए।'),
)

def run(live=False,repeats=2):
    if not live:return {'planned_calls':len(CASES)*repeats,'executed_calls':0,'live':False}
    from services.llm.provider import configured_provider
    provider=configured_provider()
    if provider is None:return {'executed_calls':0,'error':'No configured provider'}
    output=[]
    for case,text in CASES:
        values=[]
        for _ in range(repeats):
            r=analyze_semantics(text,provider)
            values.append(dict(available=r.available,risk_band=None if r.risk_score is None else 'high' if r.risk_score>=.85 else 'moderate' if r.risk_score>=.7 else 'elevated' if r.risk_score>=.55 else 'low',intent=r.intent,
                signals=sorted({str(s.code) for s in r.signals}),safety=r.is_safety_warning,requested_actions=sorted(r.requested_actions)))
        output.append(dict(id=case,runs=values,agreement={k:len({json.dumps(v[k],sort_keys=True) for v in values})==1 for k in values[0]}))
    return dict(provider=provider.name,model=provider.model_version,semantic_invocations=len(CASES)*repeats,max_http_attempts=len(CASES)*repeats*3,cases=output,
        caveat='Small synthetic repeatability probe, not a quality estimate; stable unavailable results are not successful analysis.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');p.add_argument('--repeats',type=int,choices=(2,3),default=2);p.add_argument('--output',type=Path)
    a=p.parse_args();r=run(a.live,a.repeats)
    if a.output:
        with a.output.open('x') as f:f.write(json.dumps(r,indent=2)+'\n')
    else:print(json.dumps(r,indent=2))
