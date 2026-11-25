// The questions an empty Contract conversation offers to start with. They are filled from fixed
// English wording with no model call: first about the Contract's Flagged clauses, then general
// ones for the places left over.
import { headingAndBody } from "../../clause-links";
import type { ContractDetail } from "@/lib/contract-types";

// `heading` is the Clause's own wording inside the question, to be set as the Contract's.
export type Starter = { query: string; heading?: string };

const MAX_STARTERS = 3;
const GENERAL: Starter[] = [
  { query: "What must I do under this Contract?" },
  { query: "How can this Contract be ended?" },
  { query: "What happens if either side breaks this Contract?" },
];

export function starterQuestions({ brief, clauses }: ContractDetail): Starter[] {
  const numbers = new Set(brief?.flagged_clauses.map((f) => f.clause_reference.number));
  const flagged = [...numbers].slice(0, MAX_STARTERS).map((number): Starter => {
    if (number === "0")
      return { query: "What do the Recitals say, and what does Indian law provide?" };
    const clause = clauses.find((c) => c.number === number);
    // Named only by a heading that reads as a title, as the Clause itself is shown.
    const heading = clause && headingAndBody(clause.heading, clause.text).heading;
    const subject = heading ? `Clause ${number} (${heading})` : `Clause ${number}`;
    return {
      query: `What does ${subject} say, and what does Indian law provide?`,
      heading: heading || undefined,
    };
  });
  return [...flagged, ...GENERAL].slice(0, MAX_STARTERS);
}
