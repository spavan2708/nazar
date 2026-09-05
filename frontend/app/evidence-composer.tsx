"use client";

import { apiFetch } from "./api";

import Image from "next/image";
import { AnalyzerTabs, Card, FileDropzone, LoadingStatus, Notice, PrimaryButton, type TabOption } from "./components/ui";
import { useEffect, useRef, useState } from "react";
import { appendUpload, validateUpload } from "./upload-utils";
import { type EvidenceType, type Investigation } from "./investigation-types";

type Props = {
  campaignId: string;
  disabled: boolean;
  onAdded: (investigation: Investigation) => void;
  onBusy: (busy: boolean) => void;
  onUnavailable: () => void;
};

export default function EvidenceComposer({ campaignId, disabled, onAdded, onBusy, onUnavailable }: Props) {
  const [kind, setKind] = useState<EvidenceType>("text");
  const [content, setContent] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [pending, setPending] = useState(false);
  const [retry, setRetry] = useState(false);
  const [error, setError] = useState("");
  const requestId = useRef<string | null>(null);
  const busy = useRef(false);
  const locked = disabled || pending;
  const isFile = kind === "screenshot" || kind === "audio";

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  function resetDraft() {
    requestId.current = null;
    setError("");
    setRetry(false);
    setContent("");
    setFile(null);
    setPreview("");
  }

  function selectFile(selected?: File) {
    if (!selected || locked || retry || !isFile) return;
    setError("");
    setFile(null);
    setPreview("");
    requestId.current = null;
    const message = validateUpload(selected, kind);
    if (message) setError(message);
    else {
      setFile(selected);
      if (kind === "screenshot") setPreview(URL.createObjectURL(selected));
    }
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current || disabled || (isFile ? !file : !content.trim())) return;
    busy.current = true;
    setPending(true);
    onBusy(true);
    setError("");
    requestId.current ??= crypto.randomUUID();
    try {
      const headers: Record<string, string> = { "Idempotency-Key": requestId.current };
      let body: FormData | string;
      if (isFile && file) {
        const form = new FormData();
        appendUpload(form, file, kind);
        body = form;
      } else {
        headers["Content-Type"] = "application/json";
        body = JSON.stringify(kind === "url" ? { url: content.trim() } : { text: content });
      }
      const endpoint = kind === "screenshot" ? "image" : kind;
      const response = await apiFetch(`/api/campaigns/${encodeURIComponent(campaignId)}/evidence/${endpoint}`, { method: "POST", headers, body });
      if (!response.ok) {
        if (response.status === 404) {
          onUnavailable();
          throw new Error("This investigation is no longer available. Start a new investigation to continue.");
        }
        if (response.status === 409 || response.status >= 500) {
          setRetry(true);
          throw new Error("This evidence could not be confirmed yet. Retry safely below, or refresh the investigation. You can also start a new investigation and add the text instead.");
        }
        requestId.current = null;
        setRetry(false);
        throw new Error(response.status === 413
          ? kind === "screenshot" ? "Choose an image up to 5 MiB and 16 megapixels." : "Choose a recording up to 20 MiB and two minutes long."
          : kind === "screenshot" ? "Could not read this screenshot. Try a clearer PNG, JPEG or WEBP image, or add its text as a message."
          : kind === "audio" ? "Could not read speech from this recording. Try a clearer WAV, MP3, M4A or WEBM file, or add a transcript as a message."
          : kind === "url" ? "Enter a valid HTTP or HTTPS link or domain. Other schemes are not supported."
          : "Enter a message before adding evidence.");
      }
      const next = await response.json() as Investigation;
      onAdded(next);
      resetDraft();
    } catch (failure) {
      if (failure instanceof TypeError || failure instanceof SyntaxError) {
        setRetry(true);
        setError("The response could not be confirmed. Retry this evidence safely using the same submission, or refresh the investigation.");
      } else setError(failure instanceof Error ? failure.message : "Could not add this evidence.");
    } finally {
      busy.current = false;
      setPending(false);
      onBusy(false);
    }
  }

  const types: TabOption<EvidenceType>[] = [
    { value: "text", label: "Message", icon: "message" }, { value: "url", label: "Link", icon: "link" },
    { value: "screenshot", label: "Screenshot", icon: "image" }, { value: "audio", label: "Call", icon: "audio" },
  ];
  return <Card><form onSubmit={submit} className="input-shell">
    <h3>Add related evidence</h3><p className="supporting muted mb-5">Add the next piece in the order it happened.</p>
    <AnalyzerTabs id="evidence" label="Evidence type" options={types} value={kind} disabled={locked || retry} onChange={type => { resetDraft(); setKind(type); }} />
    {types.map(type => <div key={type.value} id={`evidence-panel-${type.value}`} role="tabpanel" aria-labelledby={`evidence-tab-${type.value}`} hidden={kind !== type.value}>
      {kind === type.value && <>
        {kind === "text" && <><label htmlFor="investigation-message">Message</label><textarea maxLength={10000} id="investigation-message" value={content} disabled={locked || retry} onChange={event => { requestId.current = null; setContent(event.target.value); }} placeholder="Paste the next related message…" /></>}
        {kind === "url" && <><label htmlFor="investigation-url">Suspicious link or domain</label><input id="investigation-url" type="text" inputMode="url" autoComplete="off" autoCapitalize="none" spellCheck={false} maxLength={4096} value={content} disabled={locked || retry} onChange={event => { requestId.current = null; setContent(event.target.value); }} /><p className="caption muted mt-2">Link structure is inspected without visiting the destination.</p></>}
        {isFile && <FileDropzone id="investigation-file" label={`Choose or drop ${kind === "screenshot" ? "a screenshot" : "a recording"}`} help={kind === "screenshot" ? "PNG, JPEG or WEBP · up to 5 MiB / 16 megapixels" : "WAV, MP3, M4A or WEBM · up to 20 MiB / 2 minutes"} accept={kind === "screenshot" ? "image/png,image/jpeg,image/webp" : ".wav,.mp3,.m4a,.webm"} disabled={locked || retry} file={file} onSelect={selectFile} />}
      </>}
    </div>)}
    {preview && <Image src={preview} unoptimized width={640} height={480} alt="Selected evidence screenshot" className="mt-3 max-h-64 w-full rounded-control object-contain" />}
    {kind === "audio" && <p className="caption muted mt-3">Nazar analyzes the transcript, not the caller’s actual identity.</p>}
    <PrimaryButton type="submit" disabled={locked || (isFile ? !file : !content.trim())} className="mt-5">{pending ? "Processing evidence…" : retry ? "Retry adding evidence" : "Analyze and add"}</PrimaryButton>
    {pending && <LoadingStatus>Processing once and adding to your sequence. Recordings may take a few minutes.</LoadingStatus>}
    {error && <Notice error>{error}</Notice>}
  </form></Card>;
}
