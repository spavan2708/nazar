import AnalysisCard from "./analysis-card";
import { ExpandablePanel, RiskBadge, SignalChips } from "./components/ui";
import { evidenceLabels, stageLabels, type Evidence } from "./investigation-types";

export default function InvestigationTimeline({ evidence }: { evidence: Evidence[] }) {
  if (!evidence.length) return <div className="timeline-empty"><p>Your timeline is ready.</p><p className="supporting muted mt-2">Add the first piece of evidence to begin connecting the sequence.</p></div>;
  return <ol aria-label="Evidence timeline" className="timeline">{evidence.map(item => <li id={`evidence-${item.interaction_id}`} key={item.interaction_id} className="timeline-item">
    <div className="timeline-heading"><div><h4><span className="evidence-number">{item.order}</span>{evidenceLabels[item.type]}</h4><time dateTime={item.created_at} className="caption muted mt-2 block">{new Date(item.created_at).toLocaleString()}</time></div><span className="caption muted">Evidence {item.order}</span></div>
    <p className="caption muted">{item.type === "screenshot" ? "Text extracted from screenshot" : item.type === "audio" ? "Transcript" : item.type === "url" ? "Submitted link" : "Message"}</p>
    <p className="evidence-content">{item.display_text}</p>
    <p className="caption muted">{[item.metadata.format?.toUpperCase(), item.metadata.width && item.metadata.height ? `${item.metadata.width} × ${item.metadata.height}` : null, item.metadata.duration_seconds != null ? `${item.metadata.duration_seconds.toFixed(1)} seconds` : null, item.metadata.detected_language ? `Transcript language: ${item.metadata.detected_language}` : null].filter(Boolean).join(" · ")}</p>
    {!!item.metadata.visual?.qr_codes.length && <ExpandablePanel title="QR findings from this evidence">{item.metadata.visual.qr_codes.map((qr, index) => <div key={index}><p>{qr.explanation}</p>{qr.payee && <p className="caption muted">Recipient: {qr.payee}{qr.amount ? ` · INR ${qr.amount}` : ""}</p>}</div>)}</ExpandablePanel>}
    {item.metadata.partial_ocr && <p className="n-notice">Some screenshot languages were unavailable. Check the extracted text for omissions.</p>}
    <div className="evidence-metrics"><div><p className="caption muted">Individual risk · {item.analysis.score ?? "—"}/100</p><RiskBadge level={item.analysis.risk_level} /></div><div><p className="caption muted">Investigation after · {item.campaign_score_after}/100</p><RiskBadge level={item.campaign_risk_level_after} /></div></div>
    <p className="caption muted">{item.risk_delta > 0 ? `+${item.risk_delta} risk after this evidence` : item.risk_delta === 0 ? "No change in combined score" : `${item.risk_delta} risk after this evidence`}</p>
    <p className="supporting mt-3">{item.analysis.explanation}</p>
    {!!item.stages?.length && <div className="mt-5"><h4>Stages detected here</h4><ul className="chip-list">{item.stages.map(stage => <li key={stage} className={`chip ${item.new_stages?.includes(stage) ? "chip-new" : ""}`}>{stageLabels[stage]}{item.new_stages?.includes(stage) && <span> · New stage detected</span>}</li>)}</ul>{!!item.new_stages?.length && item.risk_delta === 0 && <p className="caption muted mt-2">The sequence has evolved even though the risk score is unchanged.</p>}</div>}
    {!!item.contextual_reinforcements?.length && <div className="reinforcement"><h4>Reinforces earlier pattern</h4>{item.contextual_reinforcements.map((cue, index) => <div key={`${cue.source_evidence_id}-${index}`}><p className="supporting mt-2">{cue.explanation}</p><p className="caption muted mt-2">Related to evidence {cue.source_evidence_order} · {stageLabels[cue.stage]}</p></div>)}<p className="caption muted mt-2">Context from earlier evidence; this does not add a signal to the current message.</p></div>}
    <h4 className="mt-5">Signals detected here</h4><SignalChips items={item.canonical_signal_codes} />
    {item.analysis.intelligence && <p className="caption muted mt-4">{(["deterministic", "ml", "llm"] as const).map(source => { const value = item.analysis.intelligence![source]; return `${source === "deterministic" ? "Rules" : source === "ml" ? "Local ML" : "AI"}: ${!value.available ? "unavailable" : value.suspicious ? "suspicious evidence" : "no suspicious evidence"}`; }).join(" · ")}</p>}
    <ExpandablePanel title="View evidence analysis"><AnalysisCard analysis={item.analysis} /></ExpandablePanel>
  </li>)}</ol>;
}
