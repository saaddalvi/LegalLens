import type { AskResponse, Citation } from "./ask-types";
import type { ClauseReference } from "./contract-types";
import { lawHref, provisionName } from "./corpus";
import { provisionText } from "./provision-text";
import { parseRefs } from "./refs";
import { TRUST_EXPLANATION, TRUST_NEEDS_EXPLANATION, TRUST_TEXT } from "./trust-labels";

// Shown with every answer and carried along when one is copied, so the caveat travels
// with the text.
export const DISCLAIMER =
  "For information only, not legal advice. Consult a qualified lawyer about your situation.";

// Shown wherever Clauses are quoted back: a scanned or converted upload can be misread.
export const CHECK_YOUR_COPY =
  "Clauses are quoted from the text LegalLens read from your upload. Check them against your own copy.";

export const clauseName = (number: string) =>
  number === "0" ? "Recitals and parties" : `Clause ${number}`;

// A value that is not a reference is shown as it is, as on screen.
const refs = (value: string) => parseRefs(value).map(provisionName).join(" and ") || value;

const indent = (text: string) =>
  text
    .split("\n")
    .map((line) => `  ${line}`)
    .join("\n");

// A Citation in full: its name and warning, the Provision's words, and where to read it.
function citationBlock(c: Citation, origin: string): string {
  const note =
    c.status === "repealed"
      ? c.superseded_by
        ? ` (repealed; now ${refs(c.superseded_by)})`
        : " (repealed)"
      : c.status === "model"
        ? " (model Act, not in force by itself)"
        : "";
  return [
    `- ${provisionName(c)}${note}`,
    indent(provisionText(c.text)),
    `  ${origin}${lawHref(c.act, c.number)}`,
  ].join("\n");
}

// An answer as plain text for pasting into a message or an email: the question, the Trust
// label, the answer, the Clauses and Citations it rests on in their own words, web sources,
// and the disclaimer. `origin` is this site's address, for the links to the Provisions.
export function answerAsText(
  result: AskResponse & { clause_references?: ClauseReference[] },
  { query, origin }: { query: string; origin: string },
): string {
  const label = TRUST_TEXT[result.trust_label];
  const parts = [
    `Question: ${query}`,
    TRUST_NEEDS_EXPLANATION.has(result.trust_label)
      ? `${label}\n${TRUST_EXPLANATION[result.trust_label]}`
      : label,
    result.answer.trim(),
  ];
  const clauses = result.clause_references ?? [];
  if (clauses.length > 0)
    parts.push(
      [
        "From your Contract:",
        CHECK_YOUR_COPY,
        ...clauses.map((r) => `- ${clauseName(r.number)}\n${indent(r.text)}`),
      ].join("\n"),
    );
  if (result.citations.length > 0)
    parts.push(["Citations:", ...result.citations.map((c) => citationBlock(c, origin))].join("\n"));
  if (result.fallback_sources.length > 0)
    parts.push(
      ["Web sources:", ...result.fallback_sources.map((s) => `- ${s.title} (${s.url})`)].join("\n"),
    );
  parts.push(DISCLAIMER);
  return parts.join("\n\n");
}
