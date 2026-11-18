import Link from "next/link";
import AskBox from "./ask-box";
import Stamp from "./stamp";
import ThemeToggle from "./theme-toggle";
import {
  CORPUS_ACTS,
  askHref,
  lawHref,
  EXAMPLE_QUERIES,
  REPEAL_NOTE,
  REPLACED_BY,
  SPECIMEN,
} from "@/lib/corpus";
import { TRUST_EXPLANATION, type TrustLabel } from "@/lib/trust-labels";

const STEPS = [
  { title: "You ask", body: "Type your question about Indian law in English or Hindi." },
  {
    title: "It is checked against the statute text",
    body: "LegalLens finds the relevant Provisions and checks every Citation against the Corpus before showing anything.",
  },
  {
    title: "You get an answer with Citations you can read",
    body: "Each Citation quotes the Provision itself, so you can read the law and not just a summary.",
  },
];

const TRUST_ORDER: TrustLabel[] = ["corpus", "corpus_and_fallback", "fallback", "none"];

// The hero's specimen: what an answer's support looks like, typeset like a
// bare-act page, with the repealed IPC section struck through.
function Specimen() {
  return (
    <Link
      href={askHref(SPECIMEN.query)}
      aria-label={`See the full answer to: ${SPECIMEN.query}`}
      className="group block border-t-2 border-ink pt-4"
    >
      <p className="text-muted">{SPECIMEN.query}</p>
      <div className="mt-5 grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1">
        <span className="condensed text-5xl text-ink sm:text-6xl">{SPECIMEN.number}.</span>
        <div className="flex flex-col gap-2 pt-1">
          <p className="text-sm text-muted">{SPECIMEN.act}</p>
          <p className="font-serif text-xl leading-snug italic">{SPECIMEN.marginalNote}</p>
        </div>
        <p className="col-start-2 mt-2 font-serif text-lg leading-relaxed">{SPECIMEN.text}</p>
      </div>
      <div className="mt-6 flex flex-wrap items-center justify-between gap-x-4 gap-y-6">
        <p className="text-sm">
          <s className="text-redtape decoration-2">{SPECIMEN.repealed}</s>{" "}
          <span className="text-muted">is repealed and replaced by {SPECIMEN.current}</span>
        </p>
        <span className="pr-2">
          <Stamp trust="corpus" large />
        </span>
      </div>
      <p className="mt-6 text-sm font-medium underline decoration-rule underline-offset-4 group-hover:decoration-ink">
        See the full answer
      </p>
    </Link>
  );
}

export default function LandingPage() {
  return (
    <>
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-4 sm:px-8">
        <header className="flex items-baseline justify-between gap-4 border-b border-rule py-5">
          <span className="condensed text-2xl">LegalLens</span>
          <div className="flex items-center gap-4 sm:gap-6">
            <Link href="/ask" className="text-sm font-medium underline underline-offset-4">
              Go to the asking screen
            </Link>
            <ThemeToggle />
          </div>
        </header>

        <div className="grid gap-12 py-12 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:gap-16 lg:py-20">
          <div className="flex flex-col gap-6">
            <h1 className="condensed text-5xl text-balance sm:text-6xl lg:text-7xl">
              Ask about Indian law. Read the law itself.
            </h1>
            <p className="max-w-[52ch] text-lg text-muted">
              Plain-language answers in English or Hindi, each backed by the statute text it comes
              from. Every Citation is checked against that text before you see it.
            </p>
            <div className="max-w-xl">
              <AskBox />
            </div>
          </div>
          <div className="lg:pt-3">
            <Specimen />
          </div>
        </div>

        <div className="flex flex-col gap-16 border-t border-rule py-14 sm:gap-20">
          <section aria-labelledby="examples" className="margin-grid">
            <h2 id="examples" className="margin-note condensed text-xl">
              Or try one of these
            </h2>
            <ul className="grid max-w-3xl gap-x-10 sm:grid-cols-2">
              {EXAMPLE_QUERIES.en.map((q) => (
                <li key={q} className="border-b border-rule">
                  <Link href={askHref(q)} className="block py-3 hover:text-stamp">
                    {q}
                  </Link>
                </li>
              ))}
              {EXAMPLE_QUERIES.hi.map((q) => (
                <li key={q} className="border-b border-rule">
                  <Link href={askHref(q)} lang="hi" className="block py-3 hover:text-stamp">
                    {q}
                  </Link>
                </li>
              ))}
            </ul>
          </section>

          <section aria-labelledby="how" className="margin-grid">
            <h2 id="how" className="margin-note condensed text-xl">
              How it works
            </h2>
            <ol className="grid max-w-3xl gap-8 sm:grid-cols-3 sm:gap-6">
              {STEPS.map((s, i) => (
                <li key={s.title} className="flex flex-col gap-2">
                  <span className="condensed text-4xl text-muted" aria-hidden="true">
                    {i + 1}.
                  </span>
                  <h3 className="font-semibold leading-snug">{s.title}</h3>
                  <p className="text-muted">{s.body}</p>
                </li>
              ))}
            </ol>
          </section>

          <section aria-labelledby="corpus" className="margin-grid">
            <h2 id="corpus" className="margin-note condensed text-xl">
              What the Corpus covers
            </h2>
            <div className="flex max-w-3xl flex-col gap-5">
              <ul className="grid gap-x-10 sm:grid-cols-2">
                {CORPUS_ACTS.map((act) => (
                  <li key={act} className="border-b border-rule">
                    <Link
                      href={lawHref(act)}
                      className="flex items-baseline justify-between gap-3 py-2 hover:bg-ledger"
                    >
                      {REPLACED_BY[act] ? (
                        <>
                          <s className="text-muted decoration-redtape decoration-2">{act}</s>
                          <span className="shrink-0 text-sm text-muted">now {REPLACED_BY[act]}</span>
                        </>
                      ) : (
                        <span>{act}</span>
                      )}
                    </Link>
                  </li>
                ))}
              </ul>
              <p className="max-w-[68ch] text-muted">{REPEAL_NOTE}</p>
            </div>
          </section>

          <section aria-labelledby="trust" className="margin-grid">
            <h2 id="trust" className="margin-note condensed text-xl">
              Trust labels explained
            </h2>
            <div className="flex max-w-3xl flex-col gap-6">
              <p>Every answer carries a label saying where its support came from.</p>
              <dl className="flex flex-col">
                {TRUST_ORDER.map((t) => (
                  <div
                    key={t}
                    className="grid gap-3 border-b border-rule py-4 sm:grid-cols-[18rem_minmax(0,1fr)] sm:items-center sm:gap-6"
                  >
                    <dt>
                      <Stamp trust={t} />
                    </dt>
                    <dd className="text-muted">{TRUST_EXPLANATION[t]}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </section>
        </div>

        <p role="note" className="border-t-4 border-ink py-6 text-lg font-medium">
          LegalLens is for information only and is not legal advice. Consult a qualified lawyer about
          your situation.
        </p>
      </main>
      <footer className="border-t border-rule px-4 py-6 text-center text-sm text-muted">
        <p>
          LegalLens answers from Indian statute text.{" "}
          <Link href="/ask" className="underline underline-offset-4">
            Ask a question
          </Link>
        </p>
      </footer>
    </>
  );
}
