import Link from "next/link";
import { ProvisionNotes, ReplacesNote, STATUS_TEXT } from "./provision-notes";
import type { Citation } from "@/lib/ask-types";
import { lawHref, provisionName } from "@/lib/corpus";
import { provisionText } from "@/lib/provision-text";

// `scope` keeps the ids of two cards for one Provision apart (the Contract brief and each
// answer in a Contract conversation can cite it).
export const cardId = (c: { act: string; number: string }, scope = "") =>
  `${scope}citation-${c.act}-${c.number}`.replace(/\W+/g, "-");

// The violet rule says this Provision was checked against the Corpus; a repealed one is
// ruled in red instead, as struck out.
export const citationRule = (c: Citation) => (c.status === "repealed" ? "border-redtape" : "border-stamp");

export function CitationName({ c }: { c: Citation }) {
  return (
    <>
      <span className={`font-semibold ${c.status === "repealed" ? "line-through decoration-redtape decoration-2" : ""}`}>
        {provisionName(c)}
      </span>{" "}
      <span className="text-muted">
        ({c.chapter}, {STATUS_TEXT[c.status]})
      </span>
    </>
  );
}

// One Citation: its Provision's name and warnings, and its text once asked for.
export default function CitationCard({
  c,
  open,
  onToggle,
  scope,
  heading: Heading,
  wayBack,
}: {
  c: Citation;
  open: boolean;
  onToggle: () => void;
  scope: string;
  heading: "h3" | "h4";
  // Offered after the heading when the reader was brought to this card from the answer.
  wayBack?: React.ReactNode;
}) {
  const panelId = `${cardId(c, scope)}-text`;
  return (
    <article id={cardId(c, scope)} className={`flex scroll-mt-4 flex-col gap-1 border-l-2 ${citationRule(c)} pl-4`}>
      <Heading>
        <button
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={onToggle}
          className="group flex min-h-11 w-full items-baseline justify-between gap-4 pt-1.5 text-left"
        >
          <span className="min-w-0 break-words">
            <CitationName c={c} />
          </span>
          <span aria-hidden="true" className="shrink-0 text-sm text-muted underline underline-offset-4 group-hover:text-ink">
            {open ? "Hide text" : "Show text"}
          </span>
        </button>
      </Heading>
      {wayBack}
      <ProvisionNotes provision={c} />
      <Link
        href={lawHref(c.act, c.number)}
        aria-label={`Open full Provision: ${provisionName(c)}`}
        className="inline-flex min-h-11 items-center self-start text-sm text-muted underline underline-offset-4 hover:text-ink"
      >
        Open full Provision
      </Link>
      {open && (
        <div id={panelId} className="flex flex-col gap-2 pb-1">
          {c.supersedes && <ReplacesNote supersedes={c.supersedes} />}
          <blockquote lang="en" className="flex flex-col gap-2 break-words bg-ledger px-4 py-3 font-serif text-lg leading-relaxed">
            {/* A gap as well as a break, so a new part stands out from a line that wrapped. */}
            {provisionText(c.text)
              .split("\n")
              .map((part, i) => (
                <p key={i} className="measure">
                  {part}
                </p>
              ))}
          </blockquote>
        </div>
      )}
    </article>
  );
}
