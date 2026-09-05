import { ExpandablePanel } from "./components/ui";
export type Grounding = {
  available: boolean;
  results: {
    source_id: string;
    chunk_id: string;
    title: string;
    source_name: string;
    source_url: string;
    guidance: string;
    topics: string[];
    matched_signals: string[];
    matched_topics: string[];
    matched_stages: string[];
    similarity: number | null;
    reviewed_on?: string | null;
    review_due?: boolean;
    relevance: "signal" | "stage" | "topic" | "semantic";
  }[];
};

const trustedHosts = new Set([
  "www.cert-in.org.in", "www.csk.gov.in", "sbi.co.in", "sbi.bank.in",
  "cyber.delhipolice.gov.in", "cybercrime.gov.in", "consumer.ftc.gov",
]);
function referenceURL(value: string) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && trustedHosts.has(url.hostname) && !url.username && !url.password && !url.port
      ? url.href : null;
  } catch { return null; }
}
function label(value: string) {
  return value.toLowerCase().replaceAll("_", " ").replace(/\botp\b/g, "OTP").replace(/\bupi\b/g, "UPI").replace(/\bkyc\b/g, "KYC");
}

export default function TrustedGuidance({ grounding, title = "Trusted guidance" }: { grounding?: Grounding | null; title?: string }) {
  if (!grounding?.available || !grounding.results.length) return null;
  return <ExpandablePanel title={title}>
    <p className="mt-2 text-xs leading-5 text-stone-gray">Retrieved guidance supports explanation; it does not determine whether an interaction is fraudulent.</p>
    <ul className="mt-3 space-y-3">{grounding.results.map(result => {
      const href = referenceURL(result.source_url);
      const relevance = result.matched_signals.length ? `Related detected signals: ${result.matched_signals.map(label).join(", ")}.`
        : result.matched_stages.length ? `Related supported stages: ${result.matched_stages.map(label).join(", ")}.`
        : result.matched_topics.length ? `Related topic in the message: ${result.matched_topics.map(label).join(", ")}. A topic mention is not a scam finding.`
        : "The wording resembles this safety topic; this is not a detector finding.";
      return <li key={result.chunk_id} className="rounded-control bg-warm-parchment p-3 text-sm leading-6 text-ink-charcoal">
        <p className="font-semibold">{result.source_name} · {result.title}</p>
        <p className="mt-1">{result.guidance}</p>
        {result.review_due && <p className="n-notice">This reference is due for review. Confirm current guidance on the official source.</p>}
        <p className="mt-2 text-xs text-stone-gray">Why this is relevant: {relevance}</p>
        {typeof result.similarity === "number" && <p className="mt-1 text-xs text-stone-gray">Retrieval similarity: {result.similarity.toFixed(2)} · Not scam probability</p>}
        {href && <a className="mt-2 inline-block text-royal-violet underline underline-offset-4" href={href} target="_blank" rel="noopener noreferrer">View source — trusted reference link (opens a new tab)</a>}
      </li>;
    })}</ul>
  </ExpandablePanel>;
}
