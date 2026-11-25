import { useState } from "react";
import { flushSync } from "react-dom";
import CitationCard, { cardId, CitationName, citationRule } from "../../citation-card";
import { LinkedText } from "../../clause-links";
import { ClauseQuote, WhereLabel } from "../../clause-quote";
import type { Citation } from "@/lib/ask-types";
import type { ContractBrief, FlaggedClause } from "@/lib/contract-types";
import { CHECK_YOUR_COPY, DISCLAIMER } from "@/lib/answer-text";
import { provisionName } from "@/lib/corpus";
import { provisionKey } from "@/lib/mentions";

// A part of the page with its own heading. `id` is where the index jumps to, and `place`
// names it on the way back from a Clause.
export function Section({
  id,
  title,
  place = title,
  children,
}: {
  id: string;
  title: string;
  place?: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} data-place={place} aria-labelledby={`${id}-heading`} className="flex scroll-mt-4 flex-col gap-3">
      <h2 id={`${id}-heading`} tabIndex={-1} data-jump-focus className="condensed self-start text-2xl">
        {title}
      </h2>
      {children}
    </section>
  );
}

// Keeps the brief's Citation cards apart from the same Provision cited in an answer below.
const SCOPE = "brief-";

// A Provision an earlier flag already shows: named again, with the way to its text there.
function ShownAbove({ c, clause, onShow }: { c: Citation; clause: string; onShow: () => void }) {
  const where = clause === "0" ? "the Recitals" : `Clause ${clause}`;
  return (
    <article className={`flex flex-col border-l-2 ${citationRule(c)} pl-4`}>
      <h3 className="break-words pt-1.5">
        <CitationName c={c} />
      </h3>
      <a
        href={`#${cardId(c, SCOPE)}`}
        aria-label={`Text shown above, under ${where}: ${provisionName(c)}`}
        onClick={(e) => {
          if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
          e.preventDefault();
          onShow();
        }}
        className="inline-flex min-h-11 items-center self-start text-sm text-muted underline underline-offset-4 hover:text-ink"
      >
        Text shown above, under {where}
      </a>
    </article>
  );
}

// Each Flagged clause, how it differs, and its Citations. A Provision cited by several flags
// has one card, under the first of them.
function FlaggedClauses({ flags }: { flags: FlaggedClause[] }) {
  const [opened, setOpened] = useState<Set<string>>(new Set());
  const firstAt = new Map<string, number>(); // Provision → the first flag that cites it
  flags.forEach((f, i) => {
    for (const c of f.citations) if (!firstAt.has(provisionKey(c))) firstAt.set(provisionKey(c), i);
  });
  const toggle = (key: string) =>
    setOpened((o) => {
      const next = new Set(o);
      if (!next.delete(key)) next.add(key);
      return next;
    });
  // Opened before scrolling, so the scroll is measured against the card's full height.
  const show = (c: Citation) => {
    flushSync(() => setOpened((o) => new Set(o).add(provisionKey(c))));
    const card = document.getElementById(cardId(c, SCOPE));
    card?.scrollIntoView?.({ block: "start" });
    card?.querySelector("button")?.focus({ preventScroll: true });
  };
  return (
    <ul className="flex flex-col gap-8">
      {flags.map((f, i) => (
        <li key={`${f.clause_reference.number}-${i}`} className="flex flex-col gap-4">
          <ClauseQuote reference={f.clause_reference} />
          <p className="measure">
            <LinkedText text={f.how_it_differs} />
          </p>
          {f.citations.map((c) => {
            const key = provisionKey(c);
            const first = firstAt.get(key)!;
            return first === i ? (
              <CitationCard
                key={key}
                c={c}
                open={opened.has(key)}
                onToggle={() => toggle(key)}
                scope={SCOPE}
                heading="h3"
              />
            ) : (
              <ShownAbove key={key} c={c} clause={flags[first].clause_reference.number} onShow={() => show(c)} />
            );
          })}
        </li>
      ))}
    </ul>
  );
}

// The Contract brief: who, what for, the Flagged clauses, key terms and who must do what.
export default function BriefView({ brief }: { brief: ContractBrief }) {
  return (
    <div className="flex flex-col gap-12">
      {/* Before the brief, so it is read with it and not after the last Clause. */}
      <div role="note" className="-mb-4 flex measure flex-col gap-1 text-sm text-muted">
        <p>{DISCLAIMER}</p>
        <p>{CHECK_YOUR_COPY}</p>
      </div>
      <Section id="parties" title="Parties">
        <ul className="measure flex flex-col gap-1">
          {brief.parties.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
      </Section>
      <Section id="purpose" title="What it is for" place="the purpose">
        <p className="measure">
          <LinkedText text={brief.purpose} />
        </p>
      </Section>
      <Section id="flagged" title="Flagged clauses">
        <p className="measure text-muted">
          A Flagged clause differs from what Indian law provides. LegalLens says how it differs,
          not whether to sign.
        </p>
        {brief.flagged_clauses.length === 0 ? (
          <p className="measure">
            No Clause was flagged. That does not mean the Contract has nothing in it worth a
            second look: LegalLens only flags a Clause it can set against a Provision in its
            Corpus.
          </p>
        ) : (
          <FlaggedClauses flags={brief.flagged_clauses} />
        )}
      </Section>
      {brief.key_terms.length > 0 && (
        <Section id="terms" title="Key terms">
          <dl className="measure flex flex-col gap-2">
            {brief.key_terms.map((t, i) => (
              <div key={`${t.label}-${i}`} className="flex flex-col">
                <dt className="font-medium">
                  <LinkedText text={t.label} />
                </dt>
                <dd>
                  <LinkedText text={t.value} />
                </dd>
                <dd>
                  <WhereLabel clauses={[t.clause]} />
                </dd>
              </div>
            ))}
          </dl>
        </Section>
      )}
      {brief.obligations.length > 0 && (
        <Section id="obligations" title="What each party must do" place="obligations">
          <div className="measure flex flex-col gap-4">
            {brief.obligations.map((p, pi) => (
              <div key={`${p.party}-${pi}`} className="flex flex-col gap-2">
                <h3 className="font-semibold">{p.party}</h3>
                <ul className="flex flex-col gap-1">
                  {p.obligations.map((o, i) => (
                    <li key={i} className="flex flex-col">
                      <span>
                        <LinkedText text={o.text} />
                      </span>
                      <WhereLabel clauses={o.clauses} />
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}
