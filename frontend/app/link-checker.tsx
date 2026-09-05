"use client";

import { apiFetch } from "./api";

import { useRef, useState } from "react";
import { LoadingStatus, NazarInputShell, Notice, PrimaryButton } from "./components/ui";
import LinkAnalysis, { type URLAnalysis } from "./link-analysis";

export default function LinkChecker() {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState<URLAnalysis | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const busy = useRef(false);

  async function check(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current || !url.trim()) return;
    busy.current = true;
    setPending(true);
    setResult(null);
    setError("");
    try {
      const response = await apiFetch(`/api/analyze/url`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim() }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Enter a valid HTTP or HTTPS link up to 4096 characters.");
      setResult(data as URLAnalysis);
    } catch (failure) {
      setError(failure instanceof TypeError ? "Could not reach Nazar. Check that the backend is running." : failure instanceof Error ? failure.message : "Could not check this link.");
    } finally {
      busy.current = false;
      setPending(false);
    }
  }

  return <NazarInputShell title="Look before you follow." description="Inspect a link’s structure without visiting its destination.">
    <form onSubmit={check}>
      <label htmlFor="link-input">Suspicious link or domain</label>
      <input id="link-input" type="text" inputMode="url" maxLength={4096} autoCapitalize="none" autoComplete="off" spellCheck={false} value={url} disabled={pending} onChange={event => { setUrl(event.target.value); setResult(null); setError(""); }} placeholder="Paste the link here…" />
      <div className="form-footer"><p className="caption muted">Links are inspected locally and never opened.<br />A low structural score does not guarantee safety.</p><PrimaryButton type="submit" disabled={!url.trim() || pending}>{pending ? "Checking…" : "Analyze link"}</PrimaryButton></div>
    </form>
    {pending && <LoadingStatus>Inspecting the link’s structure.</LoadingStatus>}
    {error && <Notice error>{error}</Notice>}
    <div aria-live="polite">{result && <LinkAnalysis urls={[result]} />}</div>
  </NazarInputShell>;
}
