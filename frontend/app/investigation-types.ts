import type { Grounding } from "./trusted-guidance";
import type { AnalysisResult } from "./analysis-card";

export type EvidenceType = "text" | "screenshot" | "url" | "audio";
export type RiskLevel = "low" | "medium" | "high" | "critical";
export type Evidence = {
  interaction_id: string;
  type: EvidenceType;
  created_at: string;
  order: number;
  display_text: string;
  extracted_text: string | null;
  transcript: string | null;
  submitted_url: string | null;
  analysis: AnalysisResult;
  canonical_signal_codes: string[];
  campaign_score_after: number;
  campaign_risk_level_after: RiskLevel;
  risk_delta: number;
  stages?: ScamStage[];
  new_stages?: ScamStage[];
  current_stage_after?: ScamStage | null;
  contextual_reinforcements?: {
    stage: ScamStage;
    source_evidence_id: string;
    source_evidence_order: number;
    explanation: string;
  }[];
  metadata: {
    visual?: { qr_codes: { kind: string; payee?: string | null; amount?: string | null; explanation: string }[] } | null;
    format: string | null;
    width: number | null;
    height: number | null;
    duration_seconds: number | null;
    detected_language: string | null;
    partial_ocr: boolean;
  };
};
export type Investigation = {
  grounding?: Grounding | null;
  campaign_id: string;
  campaign_score: number;
  risk_level: RiskLevel;
  evidence_count: number;
  canonical_signal_codes: string[];
  explanation: string;
  interactions: Evidence[];
  stages?: ScamStage[];
  stage_progression?: StageProgression[];
  current_stage?: ScamStage | null;
  stage_explanation?: string;
};
export const evidenceLabels: Record<EvidenceType, string> = {
  text: "Message", screenshot: "Screenshot", url: "Link", audio: "Call / voice note",
};
export function signalLabel(code: string) {
  const text = code.toLowerCase().replaceAll("_", " ").replace(/\botp\b/g, "OTP").replace(/\burl\b/g, "URL");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export const stageLabels = {
  IMPERSONATION: "Impersonation / trust setup",
  URGENCY_OR_PRESSURE: "Urgency / pressure",
  VERIFICATION_PRETEXT: "Verification pretext",
  LINK_REDIRECTION: "Link redirection",
  CREDENTIAL_HARVESTING: "Credential harvesting",
  PAYMENT_EXTRACTION: "Payment request",
  REMOTE_ACCESS: "Remote access / device takeover",
  AUTHENTICATION_TAKEOVER: "OTP / authentication takeover",
  INVESTMENT_LURE: "Investment lure",
} as const;
export type ScamStage = keyof typeof stageLabels;
export type StageProgression = {
  evidence_id: string;
  evidence_order: number;
  new_stages: ScamStage[];
  current_stage: ScamStage;
};
