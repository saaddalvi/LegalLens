import Link from "next/link";
import AskBox from "./ask-box";
import { CORPUS_ACTS, EXAMPLE_QUERIES, REPEAL_NOTE } from "@/lib/corpus";
import { TRUST_EXPLANATION, TRUST_TEXT, type TrustLabel } from "@/lib/trust-labels";

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

const exampleLink =
  "block rounded border border-border bg-surface px-3 py-2 text-ink hover:border-accent";

export default function LandingPage() {
  return (
    <>
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-12 px-4 py-10">
        <header className="flex flex-col gap-5">
          <div className="flex items-center justify-between gap-4">
            <span className="font-serif text-xl font-semibold">LegalLens</span>
            <Link href="/ask" className="text-sm font-medium text-primary underline">
              Go to the asking screen
            </Link>
          </div>
          <h1 className="font-serif text-4xl font-semibold leading-tight">
            Plain-language answers about Indian law, with Citations you can check
          </h1>
          <p className="text-lg text-muted">
            Ask in English or Hindi. Every answer is grounded in statute text, and every Citation is
            verified against it first.
          </p>
          <AskBox />
          <div className="flex flex-col gap-2">
            <h2 className="text-sm font-medium text-muted">Or try an example</h2>
            <ul className="grid gap-2 sm:grid-cols-2">
              {EXAMPLE_QUERIES.en.map((q) => (
                <li key={q}>
                  <Link href={`/ask?q=${encodeURIComponent(q)}`} className={exampleLink}>
                    {q}
                  </Link>
                </li>
              ))}
              {EXAMPLE_QUERIES.hi.map((q) => (
                <li key={q}>
                  <Link href={`/ask?q=${encodeURIComponent(q)}`} lang="hi" className={exampleLink}>
                    {q}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </header>

        <section aria-labelledby="how" className="flex flex-col gap-4">
          <h2 id="how" className="font-serif text-2xl font-semibold">
            How it works
          </h2>
          <ol className="grid gap-4 sm:grid-cols-3">
            {STEPS.map((s, i) => (
              <li key={s.title} className="flex flex-col gap-1 rounded border border-border bg-surface p-4">
                <span className="font-serif text-accent">Step {i + 1}</span>
                <h3 className="font-medium">{s.title}</h3>
                <p className="text-sm text-muted">{s.body}</p>
              </li>
            ))}
          </ol>
        </section>

        <section aria-labelledby="corpus" className="flex flex-col gap-4">
          <h2 id="corpus" className="font-serif text-2xl font-semibold">
            What the Corpus covers
          </h2>
          <ul className="grid gap-x-6 gap-y-1 sm:grid-cols-2">
            {CORPUS_ACTS.map((act) => (
              <li key={act}>{act}</li>
            ))}
          </ul>
          <p className="text-sm text-muted">{REPEAL_NOTE}</p>
        </section>

        <section aria-labelledby="trust" className="flex flex-col gap-4">
          <h2 id="trust" className="font-serif text-2xl font-semibold">
            Trust labels explained
          </h2>
          <p className="text-muted">Every answer carries a label saying where its support came from.</p>
          <dl className="flex flex-col gap-3">
            {TRUST_ORDER.map((t) => (
              <div key={t} className="rounded border border-border bg-surface p-3">
                <dt className="font-medium">{TRUST_TEXT[t]}</dt>
                <dd className="text-sm text-muted">{TRUST_EXPLANATION[t]}</dd>
              </div>
            ))}
          </dl>
        </section>

        <p
          role="note"
          className="rounded border-2 border-warn-border bg-warn-bg p-3 text-sm font-medium text-warn"
        >
          LegalLens is for information only and is not legal advice. Consult a qualified lawyer about
          your situation.
        </p>
      </main>
      <footer className="border-t border-border px-4 py-6 text-center text-sm text-muted">
        <p>
          LegalLens answers from Indian statute text.{" "}
          <Link href="/ask" className="underline">
            Ask a question
          </Link>
        </p>
      </footer>
    </>
  );
}
