"use client";

import { useId } from "react";
import { ExpandablePanel, RiskBadge, SignalChips, readableLabel } from "./components/ui";
import TrustedGuidance, { type Grounding } from "./trusted-guidance";
import LinkAnalysis, { type URLAnalysis } from "./link-analysis";

type SourceEvidence = {
  available: boolean;
  suspicious: boolean;
  signals: string[];
  safety_warning: boolean;
  score?: number | null;
};
type Neighbor = { text: string; similarity: number; language: string; category: string };
export type Intelligence = {
  deterministic: SourceEvidence & { risk_before_fusion: number };
  ml: SourceEvidence & { model_version?: string | null; semantic_neighbors: { available: boolean; suspicious: Neighbor[]; safe: Neighbor[] } };
  llm: SourceEvidence;
  agreement: { status: string; explanation: string };
};

export type AnalysisResult = {
  ml?: { available: boolean; scam_probability?: number | null; model_version?: string | null; input_truncated?: boolean } | null;
  grounding?: Grounding | null;
  intelligence?: Intelligence | null;
  urls?: URLAnalysis[];
  urls_truncated?: boolean;
  detected_language?: "English" | "Hindi" | "Tamil" | "Hinglish" | "Tanglish" | "Mixed" | "Unknown";
  language_confidence?: "low" | "medium";
  is_mixed_language?: boolean;
  score?: number | null;
  risk_level?: string | null;
  signals?: string[] | null;
  explanation?: string | null;
  recommended_action?: string | null;
  semantic?: {
    available?: boolean;
    intent?: string | null;
    requested_actions?: string[] | null;
    tactics?: string[] | null;
    signals?: { code: string; confidence: number }[] | null;
  } | null;
};

export const agreementLabels: Record<string, string> = {
  STRONG_AGREEMENT: "Strong agreement", PARTIAL_AGREEMENT: "Partial agreement",
  RULES_ONLY: "Rules only", ML_ONLY: "Local ML only", LLM_ONLY: "AI analysis only",
  CONFLICTING: "Sources disagree", INSUFFICIENT_EVIDENCE: "Limited evidence",
};

export default function AnalysisCard({ analysis }: { analysis: AnalysisResult }) {
  const headingId = useId();
  const hasScore = typeof analysis.score === "number" && Number.isFinite(analysis.score);
  const semantic = analysis.semantic;
  const i = analysis.intelligence;
  return <section aria-labelledby={headingId} className="result-card" data-risk={analysis.risk_level?.toLowerCase()}>
    <div className="result-header"><h3 id={headingId}>Risk assessment</h3><RiskBadge level={analysis.risk_level} /></div>
    <div className="score-row"><span className="score">{hasScore ? analysis.score : "—"}</span><span className="supporting muted">{hasScore ? "/ 100 · final risk score" : "Score unavailable"}</span></div>
    <h4>Why Nazar reached this assessment</h4>
    <p className="result-explanation">{analysis.explanation || "No explanation was provided."}</p>
    <div className="action-panel"><h4>What you should do</h4><p>{analysis.recommended_action || "No recommended action was provided."}</p></div>
    <div className="result-signals"><h4>Signals detected</h4><SignalChips items={analysis.signals} /></div>
    <TrustedGuidance grounding={analysis.grounding} />
    <ExpandablePanel title="Advanced analysis — how Nazar decided">
      {analysis.ml?.input_truncated && <p className="n-notice">The local model could only read the beginning of this long message. Rules checked the full text; split long content into shorter checks for better coverage.</p>}
      <div className="intelligence-grid">
        <div className="intelligence-item"><h4>Rules</h4><p>{i ? i.deterministic.safety_warning ? "Safety-warning context detected." : i.deterministic.suspicious ? "Suspicious requests or patterns detected." : "No explicit scam request detected." : "Source details are not available for this result."}</p>{i && <><SignalChips items={i.deterministic.signals} /><p className="caption muted">Risk before fusion: {i.deterministic.risk_before_fusion}/100</p></>}</div>
        <div className="intelligence-item"><h4>Local ML</h4><p>{i?.ml.available && i.ml.score != null ? `Local ML suspiciousness score: ${i.ml.score.toFixed(2)}` : !i && analysis.ml?.available && analysis.ml.scam_probability != null ? `Local ML suspiciousness score: ${analysis.ml.scam_probability.toFixed(2)}` : "Unavailable"}</p><p className="muted">This score is not a calibrated real-world fraud probability.</p>{i?.ml.model_version && <p className="caption muted">Model {i.ml.model_version}</p>}</div>
        <div className="intelligence-item"><h4>AI semantic analysis</h4><p>{i ? i.llm.available ? "Available" : "Unavailable — the other analysis sources still apply." : semantic?.available ? "Available" : "Unavailable — the other analysis sources still apply."}</p>{i?.llm.available && <><p>{i.llm.score != null && `Suspiciousness score: ${i.llm.score.toFixed(2)}`}</p><SignalChips items={i.llm.signals} /></>}</div>
        <div className="intelligence-item"><h4>Model agreement</h4><p>{i ? agreementLabels[i.agreement.status] ?? "Agreement unavailable" : "Agreement unavailable"}</p>{i && <p className="muted">{i.agreement.explanation}</p>}</div>
      </div>
      {semantic?.available && <ExpandablePanel title="AI interpretation details"><h4>Intent</h4><p className="supporting mt-2">{semantic.intent || "No clear intent identified."}</p><h4 className="mt-4">Requested actions</h4><SignalChips items={semantic.requested_actions} empty="None reported." /><h4 className="mt-4">Tactics</h4><SignalChips items={semantic.tactics} empty="None reported." /><h4 className="mt-4">Semantic signals</h4><SignalChips items={semantic.signals?.map(signal => signal.code)} /></ExpandablePanel>}
      {i?.ml.semantic_neighbors?.available ? <ExpandablePanel title="Semantically similar labelled examples"><p className="supporting muted">Synthetic training examples provide context, not official evidence or proof of what caused the prediction. Similarity is not scam probability.</p>{(["suspicious", "safe"] as const).map(label => <div key={label} className="mt-4"><h4>Labelled {label}</h4>{i.ml.semantic_neighbors[label].map((n, index) => <div className="neighbor-row" key={index}><blockquote>“{n.text}”</blockquote><p className="caption muted">Similarity: {n.similarity.toFixed(2)} · {n.language} · {readableLabel(n.category)}</p></div>)}</div>)}</ExpandablePanel> : <p className="caption muted mt-4">Semantic examples unavailable or disabled.</p>}
      {analysis.detected_language && <p className="caption muted mt-4">Language: {analysis.detected_language === "Unknown" ? "Uncertain" : `${analysis.is_mixed_language && analysis.detected_language !== "Mixed" ? "Mixed / " : ""}${analysis.detected_language}${analysis.language_confidence === "low" ? " (likely)" : ""}`}</p>}
    </ExpandablePanel>
    {!!analysis.urls?.length && <ExpandablePanel title="URL analysis"><LinkAnalysis urls={analysis.urls} truncated={analysis.urls_truncated} /></ExpandablePanel>}
  </section>;
}
