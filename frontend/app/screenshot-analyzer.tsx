"use client";

import { apiFetch } from "./api";

import Image from "next/image";
import { ExpandablePanel, FileDropzone, LoadingStatus, NazarInputShell, Notice, PrimaryButton, SecondaryButton } from "./components/ui";
import { useEffect, useRef, useState } from "react";
import { appendUpload, imageTypes, validateUpload } from "./upload-utils";
import AnalysisCard, { type AnalysisResult } from "./analysis-card";

type VisualEvidence = { available: boolean; limitation: string; qr_codes: { kind: string; payee?: string | null; amount?: string | null; explanation: string }[] };
type ImageResult = { visual?: VisualEvidence; extracted_text: string; analysis: AnalysisResult; ocr?: { setup_message?: string | null } };
const accepted = imageTypes;


export default function ScreenshotAnalyzer() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [extracted, setExtracted] = useState<string | null>(null);
  const [analyzedText, setAnalyzedText] = useState("");
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [pending, setPending] = useState(false);
  const [visual, setVisual] = useState<VisualEvidence | null>(null);
  const [ocrNotice, setOcrNotice] = useState("");
  const [error, setError] = useState("");
  const busy = useRef(false);

  useEffect(() => {
    return () => { if (preview) URL.revokeObjectURL(preview); };
  }, [preview]);

  function selectFile(selected?: File) {
    if (busy.current || !selected) return;
    setError("");
    setOcrNotice("");
    setVisual(null);
    setFile(null);
    setPreview("");
    setExtracted(null);
    setAnalysis(null);
    const validationError = validateUpload(selected, "screenshot");
    if (validationError) {
      setError(validationError);
    } else {
      setFile(selected);
      setPreview(URL.createObjectURL(selected));
    }
  }

  async function analyze(corrected = false) {
    if (busy.current || (!corrected && !file) || (corrected && !extracted?.trim())) return;
    busy.current = true;
    setPending(true);
    setError("");
    setAnalysis(null);
    try {
      const form = new FormData();
      if (file) appendUpload(form, file, "screenshot");
      const response = await apiFetch(`/api/analyze/${corrected ? "text" : "image"}`, {
        method: "POST",
        ...(corrected ? {
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: extracted }),
        } : { body: form }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(typeof body?.detail === "string" ? body.detail
          : response.status === 413 ? "Screenshot is too large. Choose an image up to 5 MiB."
          : "Could not analyze this screenshot. Try another image or paste the text above.");
      }
      if (corrected) {
        setAnalysis(await response.json() as AnalysisResult);
        setAnalyzedText(extracted!);
      } else {
        const result = await response.json() as ImageResult;
        setVisual(result.visual ?? null);
        setOcrNotice(result.ocr?.setup_message ?? "");
        setExtracted(result.extracted_text);
        setAnalyzedText(result.extracted_text);
        setAnalysis(result.analysis);
      }
    } catch (failure) {
      setError(failure instanceof TypeError ? "Could not reach Nazar. Check your connection and that the backend is running."
        : failure instanceof Error ? failure.message : "Could not analyze the screenshot.");
    } finally {
      busy.current = false;
      setPending(false);
    }
  }

  const edited = extracted !== null && extracted !== analyzedText;
  return <NazarInputShell title="Read between the pixels." description="Upload a screenshot. Nazar extracts its text and checks the wording for scam signs.">
    <FileDropzone id="screenshot-file" label="Choose or drop a screenshot" help="PNG, JPEG or WEBP · up to 5 MiB / 16 megapixels · English, Hindi and Tamil text" accept={accepted.join(",")} disabled={pending} file={file} onSelect={selectFile} />
    {preview && <Image src={preview} alt="Selected screenshot preview" width={640} height={480} unoptimized className="mt-4 max-h-64 w-full rounded-control object-contain" />}
    <div className="form-footer"><p className="caption muted">Text and optional QR contents are checked. Visual identity is not verified.<br />Latin-script Hinglish and Tanglish are supported.</p><PrimaryButton type="button" disabled={!file || pending} onClick={() => analyze()}>{pending ? "Analyzing…" : "Analyze screenshot"}</PrimaryButton></div>
    {pending && <LoadingStatus>Reading and analyzing your message. This may take a moment.</LoadingStatus>}
    {visual?.available && visual.qr_codes.length > 0 && <ExpandablePanel title="QR contents from this screenshot">{visual.qr_codes.map((qr, index) => <div key={index} className="mt-3"><p className="supporting">{qr.explanation}</p>{qr.payee && <p className="caption muted">Recipient: {qr.payee}{qr.amount ? ` · INR ${qr.amount}` : ""}</p>}</div>)}<p className="caption muted mt-3">{visual.limitation}</p></ExpandablePanel>}
    {ocrNotice && <Notice>{ocrNotice}</Notice>}
    {error && <Notice error>{error}</Notice>}
    <div aria-live="polite">{analysis && !edited && <AnalysisCard analysis={analysis} />}</div>
    {extracted !== null && <ExpandablePanel title="Review and correct extracted text">
      <p className="supporting muted">Check for missing or incorrect words. You can correct the text and analyze it again.</p>
      <label htmlFor="extracted-text">Text extracted from your screenshot</label>
      <textarea maxLength={10000} id="extracted-text" value={extracted} disabled={pending} onChange={event => setExtracted(event.target.value)} />
      <SecondaryButton type="button" disabled={!extracted.trim() || pending} onClick={() => analyze(true)} className="mt-3">Re-analyze text</SecondaryButton>
    </ExpandablePanel>}
    {edited && <Notice>Text changed. Re-analyze to update the result.</Notice>}
  </NazarInputShell>;
}
