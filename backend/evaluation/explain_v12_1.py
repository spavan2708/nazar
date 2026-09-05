"""Inspect frozen V12 errors without fitting or changing a classifier."""
import json
from pathlib import Path
from ml.classifier import _load_model_bundle
from ml.neighbors import explain_neighbors
from services.text_analyzer import analyze_text


def main():
    root=Path(__file__).resolve().parent
    result=json.loads((root/'v12_results.json').read_text())['results']['v2']
    selected=[]; languages=set(); categories=set()
    while len(selected)<min(10,len(result['false_negatives'])):
        row=max((r for r in result['false_negatives'] if r not in selected),key=lambda r: (r['language'] not in languages)+(r['category'] not in categories))
        selected.append(row);languages.add(row['language']);categories.add(row['category'])
    model,_,version=_load_model_bundle('v2')
    lines=['# V12.1 frozen error inspection','',
        'Source: `v12_results.json`, V4 v2 frozen evaluation. Scores are saved V12 suspiciousness scores. Error classification uses the existing 0.65 evidence threshold. Production thresholds remain 0.65 / 0.80; no model was retrained.', '',
        'All five false positives and ten false negatives selected greedily for language/category coverage (frozen order breaks ties). Neighbors use existing local MiniLM and approved training references, two per label. Cosine similarity is not scam probability or causal attribution. V3 signals are recomputed with current rules, not historical snapshots.', '']
    for title,rows in [('All five false positives',result['false_positives']),('Ten representative false negatives',selected)]:
        lines += ['## '+title,'']
        for row in rows:
            rules=analyze_text(row['text'])
            neighbors=explain_neighbors(model,model.encode([row['text']],normalize_embeddings=True)[0],version)
            if not neighbors.available: raise RuntimeError('Approved references unavailable; report not written')
            lines += [f"### {row['id']} · {row['language']} · {row['category']}",'',row['text'],'',f"True label: **{row['label']}**. V4 score: **{row['value']:.6f}**.",f"V3 signals: {', '.join(sorted(rules.signal_codes)) or 'none'}. Safety-warning context: {rules.context.is_safety_warning}.",'']
            for label,items in [('Suspicious',neighbors.suspicious),('Safe',neighbors.safe)]:
                lines += [f'- {label} neighbor (similarity {n.similarity:.4f}; {n.language}; {n.category}): {n.text}' for n in items]
            lines += ['']
    lines += [(root/'v12_1_findings.md').read_text()]
    (root/'V12_1_ERROR_ANALYSIS.md').write_text('\n'.join(lines))


if __name__=='__main__':
    main()
