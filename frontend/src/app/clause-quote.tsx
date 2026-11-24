import type { ClauseReference } from "@/lib/contract-types";

// Where in the user's own Contract something comes from. Labelled "Your Contract" so it is
// never mistaken for a Citation, which is always to a Provision.
export function WhereLabel({ clauses }: { clauses: string[] }) {
  return (
    <span className="text-sm text-muted">
      Your Contract, {clauses.length === 1 ? "Clause" : "Clauses"} {clauses.join(", ")}
    </span>
  );
}

export function ClauseQuote({ reference }: { reference: ClauseReference }) {
  return (
    <figure className="flex flex-col gap-2 border-l-2 border-ink pl-4">
      <figcaption>
        <WhereLabel clauses={[reference.number]} />
      </figcaption>
      <blockquote lang="en" className="max-w-[68ch] whitespace-pre-line break-words font-serif text-lg leading-relaxed">
        {reference.text}
      </blockquote>
    </figure>
  );
}
