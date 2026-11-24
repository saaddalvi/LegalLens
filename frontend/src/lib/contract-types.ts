import type { Citation } from "./ask-types";

// The shapes the backend returns from /contracts.
export type ContractSummary = {
  id: string;
  title: string;
  created_at: string;
  page_count: number;
  clause_count: number;
};

export type ClauseOut = { number: string; heading: string; text: string };

// The Contract brief. Every Clause number is one of the Contract's own, and every Citation was
// checked against the Corpus.
export type ClauseReference = { number: string; text: string };
export type BriefTerm = { label: string; value: string; clause: string };
export type PartyObligations = {
  party: string;
  obligations: { text: string; clauses: string[] }[];
};
export type FlaggedClause = {
  clause_reference: ClauseReference;
  how_it_differs: string;
  citations: Citation[];
};
export type ContractBrief = {
  parties: string[];
  purpose: string;
  key_terms: BriefTerm[];
  obligations: PartyObligations[];
  flagged_clauses: FlaggedClause[];
};

// brief is null for a Contract uploaded before briefs existed.
export type ContractDetail = ContractSummary & { clauses: ClauseOut[]; brief: ContractBrief | null };

// The final `answer` event of POST /contracts/stream.
export type UploadedContract = {
  id: string;
  title: string;
  clause_count: number;
  brief: ContractBrief;
};
