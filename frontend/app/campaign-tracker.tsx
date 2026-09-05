"use client";

import { apiFetch } from "./api";

import { useRef, useState } from "react";
import { Card, ExpandablePanel, LoadingStatus, Notice, PrimaryButton, RiskBadge, SecondaryButton, SignalChips } from "./components/ui";
import TrustedGuidance from "./trusted-guidance";
import EvidenceComposer from "./evidence-composer";
import InvestigationTimeline from "./investigation-timeline";
import { stageLabels, type Investigation } from "./investigation-types";

export default function CampaignTracker() {
  const [campaign, setCampaign] = useState<Investigation | null>(null);
  const [pending, setPending] = useState(false);
  const [composerBusy, setComposerBusy] = useState(false);
  const [unavailable, setUnavailable] = useState(false);
  const [error, setError] = useState("");
  const busy = useRef(false);
  async function load(create: boolean) {
    if (busy.current || composerBusy) return;
    busy.current = true;
    setPending(true);
    setError("");
    try {
      const response = await apiFetch(`/api/campaigns${create ? "" : `/${encodeURIComponent(campaign!.campaign_id)}`}`, { method: create ? "POST" : "GET", cache: "no-store" });
      if (!response.ok) {
        if (response.status === 404) setUnavailable(true);
        throw new Error(response.status === 404 ? "This investigation has expired. Start a new investigation to continue." : "Could not load the investigation. Please try again.");
      }
      setCampaign(await response.json() as Investigation);
      setUnavailable(false);
    } catch (failure) {
      setError(failure instanceof TypeError ? "Could not reach Nazar. Check that the backend is running." : failure instanceof Error ? failure.message : "Could not load the investigation.");
    } finally { setPending(false); busy.current = false; }
  }
  const currentStep = !campaign || unavailable ? 0 : campaign.evidence_count === 0 ? 1 : campaign.evidence_count === 1 ? 2 : 3;
  return <section aria-label="Investigation workspace">
    <div className="section-heading"><p className="eyebrow">Connect multiple pieces of evidence</p><h1 className="investigation-title">Your investigation</h1><p className="section-copy">Add related messages, links, screenshots or calls in order. Review what the evidence supports together.</p></div>
    <ol className="onboarding-steps" aria-label="Investigation steps">{["Start", "Add evidence", "Connect pattern", "Review warning"].map((step, index) => <li key={step} data-state={index < currentStep ? "complete" : index === currentStep ? "current" : "upcoming"} aria-current={index === currentStep ? "step" : undefined}><span aria-hidden="true">{index < currentStep ? "✓" : `0${index + 1}`}</span><div><p>{step}</p><small className="caption muted">{index < currentStep ? "Completed" : index === currentStep ? "Current step" : "Upcoming"}</small></div></li>)}</ol>
    {campaign && !unavailable && <p className="supporting">{currentStep === 1 ? "Add the first interaction below." : currentStep === 2 ? "Add another related interaction to examine the sequence. A stage may not be detected for every item." : "Review the combined warning below. You can keep adding related evidence."}</p>}
    <div className="button-row">
      {(!campaign || unavailable) && <PrimaryButton disabled={pending || composerBusy} onClick={() => void load(true)}>{pending ? "Loading…" : "Start investigation"}</PrimaryButton>}
      {campaign && !unavailable && <SecondaryButton disabled={pending || composerBusy} onClick={() => void load(false)}>Refresh investigation</SecondaryButton>}
    </div>
    <p className="caption muted mt-3">Temporary workspace: expires after one hour, up to 100 items. Restarting the backend clears investigations; reloading this page loses this view.{campaign && " Starting a new investigation replaces the sequence shown here."}</p>
    <ExpandablePanel title="How your evidence is handled"><p className="supporting muted">Evidence is not permanently saved. Screenshot extraction and audio transcription run locally; semantic text analysis may use your configured remote provider.</p></ExpandablePanel>
    {campaign && !unavailable && <ExpandablePanel title="Start a separate investigation"><p className="supporting muted">This replaces the current workspace. Finish reviewing this sequence first.</p><SecondaryButton className="mt-3" disabled={pending || composerBusy} onClick={() => void load(true)}>Start a new investigation</SecondaryButton></ExpandablePanel>}
    {pending && <LoadingStatus>Preparing your investigation.</LoadingStatus>}
    {error && <Notice error>{error}</Notice>}
    {!campaign && <div className="timeline-empty mt-6"><h3 className="mb-3">A place for the whole story.</h3><p className="supporting muted">Start an investigation, then add related evidence in sequence. Patterns and supported attack stages appear as you go.</p></div>}
    {campaign && <>
      {campaign.evidence_count > 0 && <>
      <Card className="investigation-summary">
        <div className="summary-grid" role="status">
          <div><p className="caption muted">{unavailable ? "Last known investigation risk" : "Investigation risk"}</p><p className="summary-number my-3">{campaign.campaign_score}<span className="supporting muted"> / 100</span></p><RiskBadge level={campaign.risk_level} /></div>
          <div><p className="caption muted">Evidence added</p><p className="summary-number my-3">{campaign.evidence_count}</p><p className="supporting muted">{campaign.evidence_count === 1 ? "Connected item" : "Connected items"}</p></div>
          <div><p className="caption muted">Latest supported stage</p><p className="mt-3">{campaign.current_stage ? stageLabels[campaign.current_stage] : "No stage detected yet"}</p></div>
        </div>
        <p className="supporting mt-6">{campaign.explanation}</p>
        <h4 className="mt-5">Combined signals</h4><SignalChips items={campaign.canonical_signal_codes} />
        {!!campaign.interactions.length && <p className="caption muted mt-4">Risk progression: {campaign.interactions.map(item => item.campaign_score_after).join(" → ")}</p>}
        <TrustedGuidance grounding={campaign.grounding} title="Relevant official guidance" />
      </Card>
      <Card className="progression-card"><h3>Attack progression</h3><p className="supporting muted mt-2">Risk score measures severity; supported stages explain the sequence.</p>
        {!!campaign.stage_progression?.length && <ol aria-label="Attack stage progression" className="progression">{campaign.stage_progression.map(step => <li key={step.evidence_id}><p className="caption muted">Evidence {step.evidence_order}</p><p>{step.new_stages.map(stage => stageLabels[stage]).join(" · ")}</p></li>)}</ol>}
        <p className="supporting muted mt-4">{campaign.stage_explanation ?? "Add evidence to identify supported attack stages."}</p>
      </Card>
      </>}
      <div className={unavailable ? "mt-8" : "investigation-layout"}>
        {!unavailable && <div><EvidenceComposer key={campaign.campaign_id} campaignId={campaign.campaign_id} disabled={pending} onBusy={setComposerBusy} onUnavailable={() => setUnavailable(true)} onAdded={setCampaign} /></div>}
        <div><h3 className="mb-5">Evidence timeline</h3><InvestigationTimeline evidence={campaign.interactions} /></div>
      </div>
    </>}
  </section>;
}
