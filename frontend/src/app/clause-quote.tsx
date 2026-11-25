import { Fragment } from "react";
import { ClauseLink, LinkedText } from "./clause-links";
import type { ClauseReference } from "@/lib/contract-types";

// A 44px target around a short piece of text; only the text is underlined.
const WHERE_LINK = "inline-flex min-h-11 min-w-11 items-center hover:text-ink [&>span]:underline [&>span]:underline-offset-4";

// Where in the user's own Contract something comes from. Labelled "Your Contract" so it is
// never mistaken for a Citation, which is always to a Provision.
export function WhereLabel({ clauses }: { clauses: string[] }) {
  return (
    <span className="text-sm text-muted">
      Your Contract,{" "}
      {clauses.length === 1 ? (
        <ClauseLink number={clauses[0]} className={WHERE_LINK}>
          <span>Clause {clauses[0]}</span>
        </ClauseLink>
      ) : (
        <>
          Clauses{" "}
          {clauses.map((number, i) => (
            <Fragment key={`${number}-${i}`}>
              {i > 0 && " "}
              <ClauseLink number={number} label={`Clause ${number}`} className={WHERE_LINK}>
                <span>{number}</span>
                {i < clauses.length - 1 && <b className="sr-only">,</b>}
              </ClauseLink>
            </Fragment>
          ))}
        </>
      )}
    </span>
  );
}

export function ClauseQuote({ reference }: { reference: ClauseReference }) {
  return (
    <figure className="flex flex-col gap-2 border-l-2 border-ink pl-4">
      <figcaption>
        <WhereLabel clauses={[reference.number]} />
      </figcaption>
      <blockquote lang="en" className="measure whitespace-pre-line break-words font-serif text-lg leading-relaxed">
        <LinkedText text={reference.text} except={reference.number} />
      </blockquote>
    </figure>
  );
}
