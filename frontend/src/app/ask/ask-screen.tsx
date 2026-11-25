"use client";

import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import AccountNav from "../account-nav";
import { BUTTON_CLASS, FIELD_CLASS } from "../ask-box";
import { Answer, Refusal } from "../answer-view";
import type { Stage } from "../stage-list";
import StageList from "../stage-list";
import ThemeToggle from "../theme-toggle";
import { API_URL } from "@/lib/api-url";
import { DISCLAIMER } from "@/lib/answer-text";
import type { AskResponse } from "@/lib/ask-types";
import { detectedLang, errorMessage } from "@/lib/ask-stream";
import { readEvents } from "@/lib/sse";

type Asked = { q: string };
type Outcome = {
  for: Asked;
  result: AskResponse | null;
  error: string | null;
  // The Stage that was running when answering failed, when there was one.
  failedStage?: string | null;
};
type Progress = { for: Asked; stages: Stage[] };

export default function AskScreen({ initialQuery }: { initialQuery?: string }) {
  const router = useRouter();
  const { getToken } = useAuth();
  const [query, setQuery] = useState(initialQuery ?? "");
  // The Query being answered. A new object per submission, so asking the same
  // Query again asks again.
  const [asked, setAsked] = useState<Asked | null>(
    initialQuery ? { q: initialQuery } : null,
  );
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [addressQuery, setAddressQuery] = useState(initialQuery);
  const fieldRef = useRef<HTMLTextAreaElement>(null);

  // The address is the source of truth: when it changes to another Query (a
  // link, a reload, back or forward), the ask box shows that Query and it is
  // answered, unless this screen is already answering it.
  if (initialQuery !== addressQuery) {
    setAddressQuery(initialQuery);
    setQuery(initialQuery ?? "");
    if (initialQuery !== asked?.q) setAsked(initialQuery ? { q: initialQuery } : null);
  }

  useEffect(() => {
    if (!asked) return;
    const controller = new AbortController();
    let running: string | null = null; // the latest Stage to start
    const done = (
      result: AskResponse | null,
      error: string | null,
      failedStage: string | null = null,
    ) => {
      if (!controller.signal.aborted)
        setOutcome({ for: asked, result, error, failedStage });
    };
    (async () => {
      try {
        // Clerk hands back a fresh token when the cached one is about to expire.
        const token = await getToken();
        const res = await fetch(`${API_URL}/ask/stream`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ query: asked.q }),
          signal: controller.signal,
        });
        if (!res.ok) return done(null, errorMessage(res.status));
        if (!res.body) return done(null, errorMessage(null));
        let finished = false;
        await readEvents(res.body, (name, data) => {
          if (controller.signal.aborted) return;
          if (name === "stage") {
            running = (data as Stage).id;
            setProgress((p) => ({
              for: asked,
              stages: [...(p?.for === asked ? p.stages : []), data as Stage],
            }));
          } else if (name === "answer") {
            finished = true;
            done(data as AskResponse, null);
          } else if (name === "error") {
            finished = true;
            done(null, errorMessage(503), (data as { stage?: string }).stage ?? running);
          }
        });
        if (!finished) done(null, errorMessage(null), running);
      } catch {
        done(null, errorMessage(null), running);
      }
    })();
    return () => controller.abort();
  }, [asked, getToken]);

  const current = outcome?.for === asked ? outcome : null;
  const loading = asked !== null && current === null;
  const result = current?.result ?? null;
  const error = current?.error ?? null;
  const stages = progress?.for === asked ? progress.stages : [];
  const failedStage = current?.failedStage ?? null;
  const showStages = loading || (error !== null && stages.length > 0);

  function tryAgain() {
    if (asked) setAsked({ q: asked.q });
  }

  // Starts over: the address drops the Query, which clears the ask box and the answer.
  function askAnother() {
    router.push("/ask", { scroll: false });
    setQuery("");
    setAsked(null);
    fieldRef.current?.scrollIntoView?.({ block: "center" });
    fieldRef.current?.focus({ preventScroll: true });
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    setAsked({ q });
    if (q !== initialQuery) {
      router.push(`/ask?${new URLSearchParams({ q })}`, { scroll: false });
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-10 px-4 pb-16 sm:px-8">
      <header className="border-b border-rule pt-5 pb-4">
        <div className="flex items-center justify-between gap-4">
          <h1 className="condensed text-2xl">
            <Link href="/">LegalLens</Link>
          </h1>
          <div className="flex items-center gap-4">
            <AccountNav />
            <ThemeToggle />
          </div>
        </div>
      </header>

      <form onSubmit={submit} className="flex flex-col gap-3">
        <label htmlFor="query" className="font-medium">
          Ask a question about Indian law
        </label>
        <textarea
          id="query"
          ref={fieldRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          rows={3}
          placeholder="In English or Hindi"
          className={FIELD_CLASS}
        />
        <button type="submit" disabled={loading} className={`${BUTTON_CLASS} self-start`}>
          {loading ? "Thinking…" : "Ask"}
        </button>
      </form>

      {showStages && (
        <StageList
          stages={stages}
          loading={loading}
          failedStage={failedStage}
          lang={detectedLang(asked?.q ?? "")}
        />
      )}

      {error && (
        <div role="alert" className="flex flex-col items-start gap-3 border border-rule bg-ledger px-4 py-4">
          <p>{error}</p>
          <button type="button" onClick={tryAgain} className={BUTTON_CLASS}>
            Try again
          </button>
        </div>
      )}

      {result?.response_type === "refusal" && (
        <Refusal
          key={`${asked?.q}-${result.refusal_reason}`}
          result={result}
          onReformulate={setQuery}
        />
      )}

      {result?.response_type === "answer" && <Answer key={`${asked?.q}-${result.answer}`} result={result} />}

      <footer className="flex flex-col items-start gap-6 border-t border-rule pt-6">
        {result && (
          <button type="button" onClick={askAnother} className={BUTTON_CLASS}>
            Ask another question
          </button>
        )}
        <p role="note" className="max-w-[68ch] text-sm text-muted">
          {DISCLAIMER}
        </p>
      </footer>
    </main>
  );
}
