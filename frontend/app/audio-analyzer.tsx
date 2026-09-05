"use client";

import { apiFetch } from "./api";

import { useRef, useState } from "react";
import { ExpandablePanel, FileDropzone, LoadingStatus, NazarInputShell, Notice, PrimaryButton, SecondaryButton } from "./components/ui";
import { appendUpload, validateUpload } from "./upload-utils";
import AnalysisCard, { type AnalysisResult } from "./analysis-card";

type AudioMetadata = {
  engine: string;
  detected_language: string | null;
  duration_seconds: number;
  format: string;
};
type AudioResult = { transcript: string; analysis: AnalysisResult; audio: AudioMetadata };

const languageNames: Record<string, string> = { en: "English", hi: "Hindi", ta: "Tamil" };

export default function AudioAnalyzer() {
  const [file, setFile] = useState<File | null>(null);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [analyzedText, setAnalyzedText] = useState("");
  const [metadata, setMetadata] = useState<AudioMetadata | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const busy = useRef(false);

  function selectFile(selected?: File) {
    if (busy.current || !selected) return;
    setError("");
    setFile(null);
    setTranscript(null);
    setMetadata(null);
    setAnalysis(null);
    const validationError = validateUpload(selected, "audio");
    if (validationError) {
      setError(validationError);
    } else {
      setFile(selected);
    }
  }

  async function analyze(corrected = false) {
    if (busy.current || (!corrected && !file) || (corrected && !transcript?.trim())) return;
    busy.current = true;
    setPending(true);
    setError("");
    setAnalysis(null);
    try {
      const form = new FormData();
      if (file) appendUpload(form, file, "audio");
      const response = await apiFetch(`/api/analyze/${corrected ? "text" : "audio"}`, {
        method: "POST",
        ...(corrected ? { headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: transcript }) } : { body: form }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(typeof body?.detail === "string" ? body.detail
          : response.status === 413 ? "Choose a recording up to 20 MiB and two minutes long."
          : "Could not analyze this recording. Try another file or paste a transcript in the text analyzer.");
      }
      if (corrected) {
        setAnalysis(await response.json() as AnalysisResult);
        setAnalyzedText(transcript!);
      } else {
        const result = await response.json() as AudioResult;
        setTranscript(result.transcript);
        setAnalyzedText(result.transcript);
        setMetadata(result.audio);
        setAnalysis(result.analysis);
      }
    } catch (failure) {
      setError(failure instanceof TypeError ? "Could not reach Nazar. Check that the backend is running."
        : failure instanceof Error ? failure.message : "Could not analyze this recording.");
    } finally {
      busy.current = false;
      setPending(false);
    }
  }

  const edited = transcript !== null && transcript !== analyzedText;
  return <NazarInputShell title="Listen to what’s being asked." description="Upload a call or voice note. Nazar checks the transcript, not the caller’s actual identity.">
    <FileDropzone id="audio-file" label="Choose or drop a recording" help="WAV, MP3, M4A or WEBM · up to 20 MiB / 2 minutes · English, Hindi and Tamil" accept=".wav,.mp3,.m4a,.webm,audio/wav,audio/mpeg,audio/mp4,audio/webm" disabled={pending} file={file} onSelect={selectFile} />
    <div className="form-footer"><p className="caption muted">Transcription runs locally. Temporary audio is deleted after processing. Transcript analysis may use your configured AI provider.</p><PrimaryButton type="button" disabled={!file || pending} onClick={() => analyze()}>{pending ? "Analyzing…" : "Analyze call"}</PrimaryButton></div>
    {pending && <LoadingStatus>Transcribing and analyzing. This can take up to a few minutes.</LoadingStatus>}
    {error && <Notice error>{error}</Notice>}
    <div aria-live="polite">{analysis && !edited && <AnalysisCard analysis={analysis} />}</div>
    {transcript !== null && <ExpandablePanel title="Review and correct transcript">
      <p className="supporting muted">Review the words and any links. Mixed-language speech may need correction.</p>
      {metadata && <p className="caption muted mt-3">{metadata.format.toUpperCase()} · {metadata.duration_seconds.toFixed(1)} seconds{metadata.detected_language ? ` · Speech language: ${languageNames[metadata.detected_language] ?? metadata.detected_language} (estimated)` : ""}</p>}
      <label htmlFor="audio-transcript">Transcript from your recording</label>
      <textarea maxLength={10000} id="audio-transcript" value={transcript} disabled={pending} onChange={event => setTranscript(event.target.value)} />
      <SecondaryButton type="button" disabled={!transcript.trim() || pending} onClick={() => analyze(true)} className="mt-3">Re-analyze transcript</SecondaryButton>
    </ExpandablePanel>}
    {edited && <Notice>Transcript changed. Re-analyze to update the result.</Notice>}
  </NazarInputShell>;
}
