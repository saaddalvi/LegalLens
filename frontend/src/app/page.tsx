"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Citation = {
  act: string;
  chapter: string;
  number: string;
  status: "in_force" | "repealed" | "model";
  text: string;
  superseded_by: string | null;
  supersedes: string | null;
};

type FallbackSource = { title: string; url: string; snippet: string };

type AskResponse = {
  response_type: "answer" | "refusal";
  refusal_reason: string | null;
  suggested_reformulation: string | null;
  answer: string;
  answer_language: string;
  trust_label: "corpus" | "fallback" | "corpus_and_fallback" | "none";
  citations: Citation[];
  fallback_sources: FallbackSource[];
};

const TRUST_TEXT: Record<AskResponse["trust_label"], string> = {
  corpus: "From statute text",
  fallback: "From web sources (less reliable)",
  corpus_and_fallback: "From statute text and web sources",
  none: "No supporting source found",
};

function errorMessage(status: number | null): string {
  if (status === null)
    return "We could not reach the LegalLens service. Check your connection and try again.";
  if (status === 429)
    return "You have asked too many questions in a short time. Please wait a minute and try again.";
  if (status === 503 || status >= 500)
    return "The service is unavailable right now. Please try again shortly.";
  if (status === 422)
    return "That question could not be processed. Please check it and try again.";
  return "Something went wrong. Please try again.";
}

const STATUS_TEXT: Record<Citation["status"], string> = {
  in_force: "in force",
  repealed: "repealed",
  model: "model Act, not in force by itself",
};

function CitationCard({ c }: { c: Citation }) {
  const [open, setOpen] = useState(false);
  const panelId = `citation-${c.act}-${c.number}`.replace(/\W+/g, "-");
  return (
    <article className="rounded border border-zinc-300">
      <h3 className="text-sm font-semibold">
        <button
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen(!open)}
          className="flex w-full items-start justify-between gap-2 p-3 text-left"
        >
          <span className="min-w-0 break-words">
            {c.act}, {c.number}{" "}
            <span className="font-normal text-zinc-500">
              ({c.chapter}, {STATUS_TEXT[c.status]})
            </span>
          </span>
          <span aria-hidden="true">{open ? "−" : "+"}</span>
        </button>
      </h3>
      {c.status === "repealed" && (
        <p role="note" className="mx-3 mb-3 rounded bg-red-50 p-2 text-sm text-red-800">
          This Provision has been repealed
          {c.superseded_by
            ? `. The current law is ${c.superseded_by.split("; ").join(" and ")}.`
            : "."}
        </p>
      )}
      {c.status === "model" && (
        <p role="note" className="mx-3 mb-3 rounded bg-amber-50 p-2 text-sm text-amber-900">
          This is a model Act, a template that States may adopt. It is not law in force by
          itself. Your State&apos;s own law may differ, so check it.
        </p>
      )}
      {open && (
        <div id={panelId} className="px-3 pb-3">
          {c.supersedes && (
            <p className="text-sm text-zinc-600">
              Replaces {c.supersedes.split("; ").join(" and ")}.
            </p>
          )}
          <blockquote lang="en" className="mt-1 break-words text-sm">
            {c.text}
          </blockquote>
        </div>
      )}
    </article>
  );
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${API_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      if (!res.ok) {
        setResult(null);
        setError(errorMessage(res.status));
        return;
      }
      setResult(await res.json());
    } catch {
      setResult(null);
      setError(errorMessage(null));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-4 py-8">
      <h1 className="text-2xl font-semibold">LegalLens</h1>
      <p
        role="note"
        className="rounded border border-amber-400 bg-amber-50 p-3 text-sm text-amber-900"
      >
        LegalLens is for information only and is not legal advice. Consult a
        qualified lawyer about your situation.
      </p>

      <form onSubmit={submit} className="flex flex-col gap-3">
        <label htmlFor="query" className="font-medium">
          Ask a question about Indian law
        </label>
        <textarea
          id="query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          rows={3}
          className="w-full rounded border border-zinc-300 p-2 text-base text-black"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded bg-zinc-900 px-4 py-3 text-white disabled:opacity-50 sm:self-start"
        >
          {loading ? "Thinking…" : "Ask"}
        </button>
      </form>

      {loading && (
        <p role="status" aria-label="Loading" className="animate-pulse text-zinc-600">
          Looking through the statutes…
        </p>
      )}

      {error && (
        <p
          role="alert"
          className="rounded border border-red-300 bg-red-50 p-3 text-red-800"
        >
          {error}
        </p>
      )}

      {result?.response_type === "refusal" && (
        <section
          role="status"
          aria-label="Refusal"
          className="flex flex-col gap-2 rounded border border-red-300 bg-red-50 p-4 text-red-900"
        >
          <h2 className="font-semibold">LegalLens can&apos;t help with that question</h2>
          <p lang={result.answer_language}>{result.refusal_reason ?? result.answer}</p>
          {result.suggested_reformulation && (
            <p>
              <span className="font-medium">Try asking instead: </span>
              <button
                type="button"
                onClick={() => setQuery(result.suggested_reformulation ?? "")}
                className="text-left underline"
              >
                {result.suggested_reformulation}
              </button>
            </p>
          )}
        </section>
      )}

      {result?.response_type === "answer" && (
        <section className="flex flex-col gap-4" aria-label="Answer">
          <span className="self-start rounded-full bg-zinc-200 px-3 py-1 text-xs text-black">
            {TRUST_TEXT[result.trust_label]}
          </span>
          <p lang={result.answer_language} className="whitespace-pre-wrap break-words">
            {result.answer}
          </p>

          {result.citations.length > 0 && (
            <div className="flex flex-col gap-2">
              <h2 className="font-medium">Citations</h2>
              {result.citations.map((c) => (
                <CitationCard key={`${c.act}-${c.number}`} c={c} />
              ))}
            </div>
          )}

          {result.fallback_sources.length > 0 && (
            <div className="flex flex-col gap-1">
            <h2 className="font-medium">Web sources</h2>
            <ul className="list-disc break-words pl-5 text-sm">
              {result.fallback_sources.map((s) => (
                <li key={s.url}>
                  <a href={s.url} className="underline">{s.title}</a>
                </li>
              ))}
            </ul>
            </div>
          )}
        </section>
      )}
    </main>
  );
}
