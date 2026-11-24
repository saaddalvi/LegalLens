import Link from "next/link";
import { ClauseQuote, WhereLabel } from "../../clause-quote";
import { ProvisionNotes, STATUS_TEXT } from "../../provision-notes";
import type { Citation } from "@/lib/ask-types";
import type { ContractBrief } from "@/lib/contract-types";
import { lawHref } from "@/lib/corpus";

function CitationBlock({ c }: { c: Citation }) {
  const rule = c.status === "repealed" ? "border-redtape" : "border-stamp";
  return (
    <article className={`flex flex-col gap-2 border-l-2 ${rule} pl-4`}>
      <p>
        <span className={`font-semibold ${c.status === "repealed" ? "line-through decoration-redtape decoration-2" : ""}`}>
          {c.act}, {c.number}
        </span>{" "}
        <span className="text-muted">
          ({c.chapter}, {STATUS_TEXT[c.status]})
        </span>
      </p>
      <ProvisionNotes provision={c} />
      <blockquote lang="en" className="max-w-[68ch] break-words bg-ledger px-4 py-3 font-serif text-lg leading-relaxed">
        {c.text}
      </blockquote>
      <Link
        href={lawHref(c.act, c.number)}
        aria-label={`Open full Provision: ${c.act}, ${c.number}`}
        className="self-start text-sm text-muted underline underline-offset-4 hover:text-ink"
      >
        Open full Provision
      </Link>
    </article>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="condensed text-xl">{title}</h2>
      {children}
    </section>
  );
}

// The Contract brief: who, what for, key terms, who must do what, and the Flagged clauses.
export default function BriefView({ brief }: { brief: ContractBrief }) {
  return (
    <div className="flex flex-col gap-8">
      <Section title="Parties">
        <ul className="flex flex-col gap-1">
          {brief.parties.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
      </Section>
      <Section title="What it is for">
        <p className="max-w-[68ch]">{brief.purpose}</p>
      </Section>
      {brief.key_terms.length > 0 && (
        <Section title="Key terms">
          <dl className="flex flex-col gap-3">
            {brief.key_terms.map((t, i) => (
              <div key={`${t.label}-${i}`} className="flex flex-col">
                <dt className="font-medium">{t.label}</dt>
                <dd>{t.value}</dd>
                <dd>
                  <WhereLabel clauses={[t.clause]} />
                </dd>
              </div>
            ))}
          </dl>
        </Section>
      )}
      {brief.obligations.length > 0 && (
        <Section title="What each party must do">
          <div className="flex flex-col gap-4">
            {brief.obligations.map((p, pi) => (
              <div key={`${p.party}-${pi}`} className="flex flex-col gap-2">
                <h3 className="font-semibold">{p.party}</h3>
                <ul className="flex flex-col gap-2">
                  {p.obligations.map((o, i) => (
                    <li key={i} className="flex flex-col">
                      <span>{o.text}</span>
                      <WhereLabel clauses={o.clauses} />
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Section>
      )}
      <Section title="Flagged clauses">
        {brief.flagged_clauses.length === 0 ? (
          <p className="max-w-[68ch] text-muted">
            No clause was flagged. That does not mean the Contract has nothing in it worth a
            second look: LegalLens only flags a clause it can set against a Provision in its
            Corpus.
          </p>
        ) : (
          <ul className="flex flex-col gap-8">
            {brief.flagged_clauses.map((f, i) => (
              <li key={`${f.clause_reference.number}-${i}`} className="flex flex-col gap-4">
                <ClauseQuote reference={f.clause_reference} />
                <p className="max-w-[68ch]">{f.how_it_differs}</p>
                {f.citations.map((c) => (
                  <CitationBlock key={`${c.act}-${c.number}`} c={c} />
                ))}
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}
