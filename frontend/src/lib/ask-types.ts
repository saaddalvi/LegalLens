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
