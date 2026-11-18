import type { TrustLabel } from "./trust-labels";

// The shapes the backend returns from /ask and /ask/stream.
export type Citation = {
  act: string;
  chapter: string;
  number: string;
  status: "in_force" | "repealed" | "model";
  text: string;
  superseded_by: string | null;
  supersedes: string | null;
};

export type FallbackSource = { title: string; url: string; snippet: string };

export type AskResponse = {
  response_type: "answer" | "refusal";
  refusal_reason: string | null;
  suggested_reformulation: string | null;
  answer: string;
  answer_language: string;
  trust_label: TrustLabel;
  citations: Citation[];
  fallback_sources: FallbackSource[];
};

// A Provision as the backend stores it. A Citation is one, quoted in an answer.
export type Provision = Citation;

// What /acts, /acts/{act} and /provision/{act}/{number} return.
export type ActSummary = { act: string; provisions: number };

export type ProvisionSummary = {
  number: string;
  chapter: string;
  status: Citation["status"];
  snippet: string;
};

export type ActIndex = { act: string; provisions: ProvisionSummary[] };
