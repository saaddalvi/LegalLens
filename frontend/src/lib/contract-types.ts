// The shapes the backend returns from /contracts.
export type ContractSummary = {
  id: string;
  title: string;
  created_at: string;
  page_count: number;
  clause_count: number;
};

export type ClauseOut = { number: string; heading: string; text: string };

export type ContractDetail = ContractSummary & { clauses: ClauseOut[] };

// The final `answer` event of POST /contracts/stream.
export type UploadedContract = { id: string; title: string; clause_count: number };
