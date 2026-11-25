import type { ContractSummary } from "./contract-types";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

const count = (n: number, noun: string) => `${n} ${noun}${n === 1 ? "" : "s"}`;

// "Uploaded 1 Mar 2026 · about 3 pages · 12 Clauses". The pages are "about" because a DOCX
// or pasted Contract has none of its own: the backend estimates them from its length.
export function contractFacts(c: Pick<ContractSummary, "created_at" | "page_count" | "clause_count">): string {
  return [
    `Uploaded ${formatDate(c.created_at)}`,
    `about ${count(c.page_count, "page")}`,
    count(c.clause_count, "Clause"),
  ].join("\u00a0· "); // a narrow line breaks after a dot, never before one
}
