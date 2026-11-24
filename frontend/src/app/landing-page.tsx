import Link from "next/link";
import AccountNav from "./account-nav";
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
  {
    title: "You ask",
    body: "Type your question about Indian law in English or Hindi.",
  },
  {
    title: "It is checked against the statute text",
    body: "LegalLens finds the relevant Provisions and checks every Citation against the Corpus before showing anything.",
  },
  {
    title: "You get an answer with Citations you can read",
    body: "Each Citation quotes the Provision itself, so you can read the law and not just a summary.",
  },
];

const CONTRACT_LANE = {
  title: "Or upload a Contract",
  body: "LegalLens writes a Contract brief: the parties, key terms and obligations, with each Flagged clause shown beside the Clause it comes from and how it differs from Indian law. Then ask follow-up Queries about it. Only English Contracts are accepted.",
};

// Three labels cover most answers; the five Contract and mixed variants sit behind a disclosure.
const TRUST_MAIN: TrustLabel[] = ["corpus", "fallback", "none"];
const TRUST_MORE: TrustLabel[] = [
  "corpus_and_fallback",
  "contract",
  "contract_and_corpus",
  "contract_and_fallback",
  "contract_corpus_and_fallback",
];

type Act = (typeof CORPUS_ACTS)[number];
// Six Acts up front; the rest, with the repealed ones last, behind "See all 15".
const FEATURED_ACTS: Act[] = [
  "Constitution of India",
  "Bharatiya Nyaya Sanhita",
  "Bharatiya Nagarik Suraksha Sanhita",
  "Bharatiya Sakshya Adhiniyam",
  "Indian Contract Act",
  "Consumer Protection Act",
];
const isRepealed = (act: Act) => Boolean(REPLACED_BY[act]);
const MORE_ACTS: Act[] = [
  ...CORPUS_ACTS.filter((a) => !FEATURED_ACTS.includes(a) && !isRepealed(a)),
  ...CORPUS_ACTS.filter(isRepealed),
];

function ActList({ acts }: { acts: Act[] }) {
  return (
    <ul className="grid gap-x-10 sm:grid-cols-2">
      {acts.map((act) => (
        <li key={act} className="border-b border-rule">
          <Link
            href={lawHref(act)}
            className="flex items-baseline justify-between gap-3 py-2 hover:bg-ledger"
          >
            {REPLACED_BY[act] ? (
              <>
                <s className="text-muted decoration-redtape decoration-2">
                  {act}
                </s>
                <span className="shrink-0 text-sm text-muted">
                  now {REPLACED_BY[act]}
                </span>
              </>
            ) : (
              <span>{act}</span>
            )}
          </Link>
        </li>
      ))}
    </ul>
  );
}

function TrustList({ labels }: { labels: TrustLabel[] }) {
  return (
    <dl className="flex flex-col">
      {labels.map((t) => (
        <div
          key={t}
          className="grid gap-3 border-b border-rule py-4 lg:grid-cols-[18rem_minmax(0,1fr)] lg:items-center lg:gap-6"
        >
          <dt>
            <Stamp trust={t} />
          </dt>
          <dd className="text-muted">{TRUST_EXPLANATION[t]}</dd>
        </div>
      ))}
    </dl>
  );
}

const DISCLOSURE = "group flex flex-col gap-3";
const SUMMARY =
  "inline-flex min-h-11 cursor-pointer list-none items-center self-start font-medium underline underline-offset-4 [&::-webkit-details-marker]:hidden";

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
        <span className="condensed text-5xl text-ink sm:text-6xl">
          {SPECIMEN.number}.
        </span>
        <div className="flex flex-col gap-2 pt-1">
          <p className="text-sm text-muted">{SPECIMEN.act}</p>
          <p className="font-serif text-xl leading-snug italic">
            {SPECIMEN.marginalNote}
          </p>
        </div>
        <p className="col-start-2 mt-2 font-serif text-lg leading-relaxed">
          {SPECIMEN.text}
        </p>
      </div>
      <div className="mt-6 flex flex-wrap items-center justify-between gap-x-4 gap-y-6">
        <p className="text-sm">
          <s className="text-redtape decoration-2">{SPECIMEN.repealed}</s>{" "}
          <span className="text-muted">
            is repealed and replaced by {SPECIMEN.current}
          </span>
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
        <header className="flex items-center justify-between gap-4 border-b border-rule py-3">
          <span className="condensed text-2xl">LegalLens</span>
          <div className="flex items-center gap-4 sm:gap-6">
            <Link
              href="/ask"
              className="inline-flex min-h-11 items-center text-sm font-medium underline underline-offset-4"
            >
              Go to the asking screen
            </Link>
            <AccountNav />
            <ThemeToggle />
          </div>
        </header>

        <div className="grid gap-12 py-12 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:gap-16 lg:py-20">
          <div className="flex flex-col gap-6">
            <h1 className="condensed text-5xl text-balance sm:text-6xl lg:text-7xl">
              <span className="block">Ask about Indian law.</span>{" "}
              <span className="block">Read the law itself.</span>
            </h1>
            <p className="max-w-[52ch] text-lg text-pretty text-muted">
              Plain-language answers in English or Hindi, each backed by the
              statute text it comes from. Every Citation is checked against that
              text before you see it.
            </p>
            <p
              lang="hi"
              className="max-w-[52ch] text-lg leading-relaxed text-pretty text-muted"
            >
              हिंदी में भी पूछिए। हर उत्तर कानून के मूल पाठ से जाँचा जाता है।
            </p>
            <div className="grid gap-8 sm:grid-cols-[minmax(0,1fr)_13rem] sm:gap-0">
              <div className="sm:pr-8">
                <AskBox />
              </div>
              <div className="flex flex-col items-start gap-3 border-t border-rule pt-6 sm:border-t-0 sm:border-l sm:pt-0 sm:pl-6">
                <h2 className="font-medium">Have a Contract?</h2>
                <p className="text-sm text-muted">
                  Get a Contract brief with its Flagged clauses. Only English
                  Contracts are accepted.
                </p>
                <Link
                  href="/contracts"
                  className="text-base font-semibold underline underline-offset-4"
                >
                  Upload a Contract
                </Link>
              </div>
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
                  <Link
                    href={askHref(q)}
                    className="block py-3 hover:text-stamp"
                  >
                    {q}
                  </Link>
                </li>
              ))}
              {EXAMPLE_QUERIES.hi.map((q) => (
                <li key={q} className="border-b border-rule">
                  <Link
                    href={askHref(q)}
                    lang="hi"
                    className="block py-3 hover:text-stamp"
                  >
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
            <div>
              <ol className="grid max-w-3xl gap-8 sm:grid-cols-3 sm:gap-6">
                {STEPS.map((s, i) => (
                  <li key={s.title} className="flex flex-col gap-2">
                    <span
                      className="condensed text-4xl text-muted"
                      aria-hidden="true"
                    >
                      {i + 1}.
                    </span>
                    <h3 className="font-semibold leading-snug">{s.title}</h3>
                    <p className="text-muted">{s.body}</p>
                  </li>
                ))}
              </ol>
              <div className="mt-8 max-w-3xl border-t border-rule pt-6 sm:mt-10">
                <h3 className="font-semibold leading-snug">
                  {CONTRACT_LANE.title}
                </h3>
                <p className="mt-2 max-w-[68ch] text-muted">
                  {CONTRACT_LANE.body}
                </p>
              </div>
            </div>
          </section>

          <section aria-labelledby="corpus" className="margin-grid">
            <h2 id="corpus" className="margin-note condensed text-xl">
              What the Corpus covers
            </h2>
            <div className="flex max-w-3xl flex-col gap-5">
              <ActList acts={FEATURED_ACTS} />
              <details className={DISCLOSURE}>
                <summary className={SUMMARY}>
                  <span className="group-open:hidden">
                    See all {CORPUS_ACTS.length} Acts
                  </span>
                  <span className="hidden group-open:inline">
                    Show fewer Acts
                  </span>
                </summary>
                <ActList acts={MORE_ACTS} />
              </details>
              <p className="max-w-[68ch] text-muted">{REPEAL_NOTE}</p>
            </div>
          </section>

          <section aria-labelledby="trust" className="margin-grid">
            <h2 id="trust" className="margin-note condensed text-xl">
              Trust labels explained
            </h2>
            <div className="flex max-w-3xl flex-col gap-6">
              <p>
                Every answer carries a label saying where its support came from.
              </p>
              <TrustList labels={TRUST_MAIN} />
              <details className={DISCLOSURE}>
                <summary className={SUMMARY}>
                  <span className="group-open:hidden">
                    Labels for Contracts and mixed sources ({TRUST_MORE.length})
                  </span>
                  <span className="hidden group-open:inline">
                    Hide Contract and mixed labels
                  </span>
                </summary>
                <TrustList labels={TRUST_MORE} />
              </details>
            </div>
          </section>
        </div>

        <p
          role="note"
          className="border-t-4 border-ink py-6 text-lg font-medium"
        >
          LegalLens is for information only and is not legal advice. Consult a
          qualified lawyer about your situation.
        </p>
      </main>
      <footer className="border-t border-rule px-4 py-6 text-center text-sm text-muted">
        <p>
          LegalLens answers from Indian statute text.{" "}
          <Link
            href="/ask"
            className="inline-flex min-h-11 items-center underline underline-offset-4"
          >
            Ask a question
          </Link>
        </p>
      </footer>
    </>
  );
}
