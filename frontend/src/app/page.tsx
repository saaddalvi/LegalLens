"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Citation = {
  act: string;
  chapter: string;
  number: string;
  status: "in_force" | "repealed";
  text: string;
  superseded_by: string | null;
};

type FallbackSource = { title: string; url: string; snippet: string };

type AskResponse = {
  answer: string;
  answer_language: string;
  trust_label: "corpus" | "fallback" | "corpus_and_fallback";
  citations: Citation[];
  fallback_sources: FallbackSource[];
};

const TRUST_TEXT: Record<AskResponse["trust_label"], string> = {
  corpus: "From statute text",
  fallback: "From web sources (less reliable)",
  corpus_and_fallback: "From statute text and web sources",
};

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
    try {
      const res = await fetch(`${API_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setResult(await res.json());
    } catch {
      setResult(null);
      setError("Something went wrong. Please try again.");
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
          className="rounded border border-zinc-300 p-2 text-black"
        />
        <button
          type="submit"
          disabled={loading}
          className="self-start rounded bg-zinc-900 px-4 py-2 text-white disabled:opacity-50"
        >
          {loading ? "Thinking…" : "Ask"}
        </button>
      </form>

      {error && <p role="alert" className="text-red-700">{error}</p>}

      {result && (
        <section className="flex flex-col gap-4" aria-label="Answer">
          <span className="self-start rounded-full bg-zinc-200 px-3 py-1 text-xs text-black">
            {TRUST_TEXT[result.trust_label]}
          </span>
          <p className="whitespace-pre-wrap">{result.answer}</p>

          {result.citations.length > 0 && (
            <div className="flex flex-col gap-2">
              <h2 className="font-medium">Citations</h2>
              {result.citations.map((c) => (
                <article
                  key={`${c.act}-${c.number}`}
                  className="rounded border border-zinc-300 p-3"
                >
                  <h3 className="text-sm font-semibold">
                    {c.act}, {c.number}{" "}
                    <span className="font-normal text-zinc-500">
                      ({c.chapter}, {c.status === "repealed" ? "repealed" : "in force"})
                    </span>
                  </h3>
                  {c.superseded_by && (
                    <p className="text-sm text-red-700">
                      Repealed. See {c.superseded_by}.
                    </p>
                  )}
                  <blockquote lang="en" className="mt-1 text-sm">
                    {c.text}
                  </blockquote>
                </article>
              ))}
            </div>
          )}

          {result.fallback_sources.length > 0 && (
            <ul className="list-disc pl-5 text-sm">
              {result.fallback_sources.map((s) => (
                <li key={s.url}>
                  <a href={s.url} className="underline">{s.title}</a>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </main>
  );
}
