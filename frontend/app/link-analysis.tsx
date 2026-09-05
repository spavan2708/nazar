import { ExpandablePanel, RiskBadge, readableLabel } from "./components/ui";
export type URLAnalysis = {
  normalized_url: string | null;
  hostname: string | null;
  domain: string | null;
  indicators: { code: string; description: string }[];
  structural_risk_score: number | null;
  risk_level: "low" | "medium" | "high" | "critical" | null;
  valid: boolean;
  explanation: string;
};
export default function LinkAnalysis({ urls, truncated = false }: { urls: URLAnalysis[]; truncated?: boolean }) {
  return <section aria-label="Link analysis" className="mt-6">
    <p className="supporting muted">Offline structure checks only. Links have not been opened. A low concern score does not mean a link is safe.</p>
    <ul className="mt-4 space-y-4">{urls.map((url, index) => <li key={index} className="result-card link-result" data-risk={url.risk_level}>
      <div className="result-header"><h3 dir="ltr">{url.domain ?? `Link ${index + 1} could not be analyzed`}</h3><RiskBadge level={url.risk_level} /></div>
      {url.valid && <div className="score-row"><span className="score">{url.structural_risk_score ?? "—"}</span><span className="supporting muted">/ 100 · structural concern</span></div>}
      <p className="result-explanation">{url.explanation}</p>
      {url.normalized_url && <p dir="ltr" className="supporting muted mt-3">{url.normalized_url}</p>}
      {!!url.indicators.length && <ExpandablePanel title="Link structure details"><ul className="space-y-3">{url.indicators.map(indicator => <li key={indicator.code}><h4>{readableLabel(indicator.code)}</h4><p className="supporting muted mt-1">{indicator.description}</p></li>)}</ul></ExpandablePanel>}
    </li>)}</ul>
    {truncated && <p className="n-notice">Only the first 20 distinct links were inspected. Check remaining links separately.</p>}
  </section>;
}
