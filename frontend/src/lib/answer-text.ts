import type { AskResponse, Citation } from "./ask-types";

// Shown on the asking screen and carried along when an answer is copied, so the
// caveat travels with the text.
export const DISCLAIMER =
  "For information only, not legal advice. Consult a qualified lawyer about your situation.";

const refs = (value: string) => value.split("; ").join(" and ");

function citationLine(c: Citation): string {
  const note =
    c.status === "repealed"
      ? c.superseded_by
        ? ` (repealed; now ${refs(c.superseded_by)})`
        : " (repealed)"
      : c.status === "model"
        ? " (model Act, not in force by itself)"
        : "";
  return `- ${c.act}, ${c.number}${note}`;
}

// An answer as plain text for pasting into a message or an email: the answer,
// its Citations and web sources, and the disclaimer.
export function answerAsText(result: AskResponse): string {
  const parts = [result.answer.trim()];
  if (result.citations.length > 0)
    parts.push(["Citations:", ...result.citations.map(citationLine)].join("\n"));
  if (result.fallback_sources.length > 0)
    parts.push(
      ["Web sources:", ...result.fallback_sources.map((s) => `- ${s.title} (${s.url})`)].join("\n"),
    );
  parts.push(DISCLAIMER);
  return parts.join("\n\n");
}
