"use client";

import { apiFetch } from "./api";

import { useEffect, useState, useSyncExternalStore } from "react";
import AudioAnalyzer from "./audio-analyzer";
import LinkChecker from "./link-checker";
import ScreenshotAnalyzer from "./screenshot-analyzer";
import MessageAnalyzer from "./message-analyzer";
import CampaignTracker from "./campaign-tracker";
import { AnalyzerTabs, Icon, SectionHeading, type TabOption } from "./components/ui";

type Mode = "message" | "link" | "screenshot" | "audio";
const modes: TabOption<Mode>[] = [
  { value: "message", label: "Message", icon: "message" }, { value: "link", label: "Link", icon: "link" },
  { value: "screenshot", label: "Screenshot", icon: "image" }, { value: "audio", label: "Call", icon: "audio" },
];
function subscribeNavigation(onChange: () => void) {
  window.addEventListener("hashchange", onChange);
  return () => window.removeEventListener("hashchange", onChange);
}
function navigationSnapshot() { return window.location.hash; }

export default function Home() {
  const hash = useSyncExternalStore(subscribeNavigation, navigationSnapshot, () => "");
  const investigating = hash === "#investigation";
  useEffect(() => {
    if (!hash) return;
    const target = document.getElementById(hash.slice(1));
    target?.scrollIntoView({ block: "start" });
    target?.focus({ preventScroll: true });
  }, [hash]);
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "error" | "network-error">("checking");
  const [mode, setMode] = useState<Mode>("message");
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    async function checkBackend() {
      try {
        const response = await apiFetch(`/health`, { signal: controller.signal });
        if (!response.ok) { if (active) setBackendStatus("error"); return; }
        const data = await response.json();
        if (active) setBackendStatus(data.status === "healthy" ? "online" : "error");
      } catch { if (active) setBackendStatus("network-error"); }
    }
    void checkBackend();
    return () => { active = false; controller.abort(); };
  }, []);
  const status = backendStatus === "checking" ? "Connecting…" : backendStatus === "online" ? "Ready to check" : "Service unavailable";
  return <>
    <a className="skip-link" href={investigating ? "#investigation" : "#analyze"}>Skip to workspace</a>
    <header className="site-header"><div className="container header-inner">
      <a className="wordmark" href="#top" aria-label="Nazar home"><Icon name="eye" />NAZAR</a>
      <nav aria-label="Main navigation" className="site-nav"><a href="#analyze" aria-current={!investigating && hash !== "#how-it-works" ? "page" : undefined}>Analyze</a><a href="#investigation" aria-current={investigating ? "page" : undefined}>Investigation</a><a className="nav-how" href="#how-it-works" aria-current={hash === "#how-it-works" ? "location" : undefined}>How Nazar works</a></nav>
      <p className="system-status" role="status"><span className="status-dot" data-online={backendStatus === "online"} />{status}</p>
    </div></header>
    <main id="top" tabIndex={-1}>
      <div hidden={investigating}>
      <section className="container hero" aria-labelledby="hero-title">
        <div className="hero-copy"><p className="eyebrow">Digital safety, made understandable.</p><h1 id="hero-title">One warning before<br />one wrong click.</h1><p>Check one suspicious message, link, screenshot or call. Have several related interactions? Connect them in an investigation.</p><div className="button-row"><a className="n-button n-button-primary" href="#analyze">Check something suspicious<Icon /></a><a className="n-button n-button-ghost" href="#investigation">Start an investigation</a></div></div>
        <div className="hero-art" aria-label="Illustration of Nazar features, not a live analysis">
          <div className="demo-card demo-main"><div className="demo-label"><Icon name="eye" /> A little clarity, before a decision.</div><h3>Recognize the request behind the message.</h3><p className="muted">Understand what you’re being asked to share, install or send.</p><ul className="chip-list"><li className="chip">OTP request</li><li className="chip">Urgency</li></ul></div>
          <div className="demo-card demo-floating"><div><p className="caption">Connect the sequence</p><p>Remote access → OTP request</p></div><Icon /></div>
          <div className="demo-card demo-bottom"><p className="caption muted">Go beyond a score</p><p className="supporting">Signals. Explanations. Trusted guidance.</p></div>
          <p className="hero-footnote">Illustrative product features · Your result comes from your evidence.</p>
        </div>
      </section>
      <section id="analyze" tabIndex={-1} className="container workspace-section" aria-labelledby="workspace-title">
        <div className="workspace-heading"><div><p className="eyebrow">Check one piece of evidence</p><h2 id="workspace-title">What do you want to check?</h2><p className="supporting muted">Add evidence, analyze it, then review the warning and safe next steps.</p></div><p className="caption muted" role="status">{status}</p></div>
        <div className="n-card workspace-card">
          <p className="workspace-label caption">1 / Choose evidence type</p>
          <AnalyzerTabs id="analyzer" label="Choose evidence type" options={modes} value={mode} onChange={setMode} />
          {modes.map(option => <div key={option.value} id={`analyzer-panel-${option.value}`} role="tabpanel" aria-labelledby={`analyzer-tab-${option.value}`} hidden={mode !== option.value} className="workspace-panel">
            {option.value === "message" ? <MessageAnalyzer /> : option.value === "link" ? <LinkChecker /> : option.value === "screenshot" ? <ScreenshotAnalyzer /> : <AudioAnalyzer />}
          </div>)}
        </div>
        {(backendStatus === "error" || backendStatus === "network-error") && <p className="n-notice" role="status">{backendStatus === "error" ? "The analysis service responded with an error." : "The analysis service could not be reached. Check the connection and backend availability."} Your input stays here while you reconnect.</p>}
      </section>
      <section className="narrative-band" aria-labelledby="sequence-title"><div className="container narrative-inner"><div><p className="eyebrow">For multiple related interactions</p><h2 id="sequence-title">More than one suspicious interaction?</h2><p>One message can be ambiguous. A sequence can reveal a pattern.</p><a className="n-button n-button-outline" href="#investigation">Start an investigation<Icon /></a></div><div><ol className="narrative-steps" aria-label="Illustrative sequence"><li><span className="sequence-number">01</span><span className="sequence-label">Impersonation</span><Icon /></li><li><span className="sequence-number">02</span><span className="sequence-label">Verification</span><Icon /></li><li><span className="sequence-number">03</span><span className="sequence-label">Remote access</span><Icon /></li><li><span className="sequence-number">04</span><span className="sequence-label">OTP request</span><Icon /></li></ol><p className="caption">Illustrative sequence. Detected stages depend on the evidence you add.</p></div></div></section>
      </div>
      <div id="investigation" tabIndex={-1} hidden={!investigating} className="container section investigation-view"><CampaignTracker /></div>
      <section id="how-it-works" tabIndex={-1} hidden={investigating} className="container section" aria-label="How Nazar works"><SectionHeading eyebrow="Designed to explain" title="A clearer picture. A considered next step.">Nazar brings different kinds of analysis together while keeping their limitations visible.</SectionHeading><div className="how-grid">
        <div className="how-item"><span className="caption">01 / Add</span><h3>Add something suspicious.</h3><p className="supporting muted">Paste a message or link, or choose a screenshot or recording. Keep the original wording.</p></div>
        <div className="how-item"><span className="caption">02 / Analyze</span><h3>Nazar examines it.</h3><p className="supporting muted">Select the analyze button. Nazar checks requests, pressure tactics and links using available analysis sources.</p></div>
        <div className="how-item"><span className="caption">03 / Review</span><h3>Understand the warning.</h3><p className="supporting muted">Read practical next steps and relevant official guidance. A score supports your judgment; it cannot confirm fraud or guarantee safety.</p></div>
      </div></section>
    </main>
    <footer className="site-footer"><div className="container footer-inner"><div><a href="#top" className="wordmark"><Icon name="eye" />NAZAR</a><p>One warning before one wrong click.</p><p>Clarity before action. Always verify important requests through a channel you trust.</p></div><nav className="footer-links" aria-label="Footer navigation"><a href="#analyze">Analyze</a><a href="#investigation">Investigation</a><a href="#how-it-works">How it works</a></nav></div></footer>
  </>;
}
