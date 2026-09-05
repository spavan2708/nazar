"use client";

import { apiFetch } from "./api";

import { useRef, useState, type FormEvent } from "react";
import AnalysisCard, { type AnalysisResult } from "./analysis-card";
import { Icon, LoadingStatus, NazarInputShell, Notice, PrimaryButton } from "./components/ui";

export default function MessageAnalyzer() {
  const [text, setText] = useState("");
  const [pending, setPending] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState("");
  const busy = useRef(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current || !text.trim()) return;
    busy.current = true; setPending(true); setAnalysis(null); setError("");
    try {
      const response = await apiFetch(`/api/analyze/text`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : `Analysis request failed (${response.status}). Please try again.`);
      setAnalysis(data as AnalysisResult);
    } catch (failure) {
      setError(failure instanceof TypeError ? "Could not reach Nazar. Check your connection and that the backend is running." : failure instanceof Error ? failure.message : "Could not analyze this message.");
    } finally { busy.current = false; setPending(false); }
  }
  return <NazarInputShell title="Paste the suspicious message below." description="Nazar checks requests, pressure tactics, links and account threats. Keep the original wording.">
    <form onSubmit={submit}>
      <label htmlFor="message-input">Message to check</label>
      <textarea maxLength={10000} aria-describedby="message-help" id="message-input" placeholder="Paste the message that made you pause…" value={text} disabled={pending} onChange={event => { setText(event.target.value); setAnalysis(null); setError(""); }} />
      <div className="form-footer"><p id="message-help" className="caption muted">{text.length.toLocaleString()} / 10,000 characters.<br />English, Hindi, Tamil, Hinglish & Tanglish.<br />Optional AI analysis may use your configured provider.</p><PrimaryButton type="submit" disabled={!text.trim() || pending}>{pending ? "Analyzing…" : "Analyze message"}<Icon /></PrimaryButton></div>
    </form>
    {pending && <LoadingStatus>Looking for requests, pressure and suspicious patterns.</LoadingStatus>}
    {error && <Notice error>{error}</Notice>}
    <div aria-live="polite">{analysis && <AnalysisCard analysis={analysis} />}</div>
  </NazarInputShell>;
}
