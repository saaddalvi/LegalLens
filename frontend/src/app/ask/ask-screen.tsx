"use client";

import { SignInButton, useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { BUTTON_CLASS, FIELD_CLASS } from "../ask-box";
import { Answer, Refusal } from "../answer-view";
import type { Stage } from "../stage-list";
import StageList from "../stage-list";
import SiteHeader from "../site-header";
import { API_URL } from "@/lib/api-url";
import { DISCLAIMER } from "@/lib/answer-text";
import type { AskResponse } from "@/lib/ask-types";
import { detectedLang, errorMessage } from "@/lib/ask-stream";
import { retryAfterSeconds } from "@/lib/daily-cap";
import { readEvents } from "@/lib/sse";

// The longest Query the backend accepts, and how close to it the count of what is left shows.
const MAX_QUERY = 2000;
const COUNT_FROM = 200;

type Asked = { q: string };
type Outcome = {
  for: Asked;
  result: AskResponse | null;
  error: string | null;
  // The service refused the session token.
  unauthorized?: boolean;
  // The Stage that was running when answering failed, when there was one.
  failedStage?: string | null;
};
type Progress = { for: Asked; stages: Stage[] };

export default function AskScreen({ initialQuery }: { initialQuery?: string }) {
  const router = useRouter();
  const { getToken, isSignedIn } = useAuth();
  const [query, setQuery] = useState(initialQuery ?? "");
  // The Query being answered. A new object per submission, so asking the same
  // Query again asks again.
  const [asked, setAsked] = useState<Asked | null>(
    initialQuery ? { q: initialQuery } : null,
  );
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [addressQuery, setAddressQuery] = useState(initialQuery);
  const [missing, setMissing] = useState(false);
  const fieldRef = useRef<HTMLTextAreaElement>(null);
  const submitRef = useRef<HTMLButtonElement>(null);

  // The address is the source of truth: when it changes to another Query (a
  // link, a reload, back or forward), the ask box shows that Query and it is
  // answered, unless this screen is already answering it.
  if (initialQuery !== addressQuery) {
    setAddressQuery(initialQuery);
    setQuery(initialQuery ?? "");
    setMissing(false);
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
      unauthorized = false,
    ) => {
      if (!controller.signal.aborted)
        setOutcome({ for: asked, result, error, failedStage, unauthorized });
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
        if (!res.ok) {
          const message = errorMessage(res.status, retryAfterSeconds(res));
          return done(null, message, null, res.status === 401);
        }
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

  // The button pressed goes away with the error, so focus moves to Ask.
  function tryAgain() {
    if (!asked) return;
    setAsked({ q: asked.q });
    submitRef.current?.focus();
  }

  // Puts text in the ask box and takes the reader to it.
  function fillAskBox(q: string) {
    setQuery(q);
    setMissing(false);
    fieldRef.current?.scrollIntoView?.({ block: "center" });
    fieldRef.current?.focus({ preventScroll: true });
  }

  // Starts over: the address drops the Query, which clears the ask box and the answer.
  function askAnother() {
    router.push("/ask", { scroll: false });
    setAsked(null);
    fillAskBox("");
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    // The button stays focusable while an answer is being written, so it is checked here.
    if (loading) return;
    const q = query.trim();
    if (!q) {
      setMissing(true);
      fieldRef.current?.focus();
      return;
    }
    setAsked({ q });
    if (q !== initialQuery) {
      router.push(`/ask?${new URLSearchParams({ q })}`, { scroll: false });
    }
  }

  const left = MAX_QUERY - query.length;

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-10 px-4 pb-16 sm:px-8">
      <SiteHeader current="ask" />

      <form onSubmit={submit} className="flex flex-col gap-3">
        <h1 className="condensed text-balance text-3xl">
          <label htmlFor="query">Ask a question about Indian law</label>
        </h1>
        <p lang="hi" className="-mt-1 text-muted">
          आप हिंदी में भी पूछ सकते हैं।
        </p>
        <textarea
          id="query"
          ref={fieldRef}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setMissing(false);
          }}
          lang={query ? detectedLang(query) : undefined}
          rows={3}
          maxLength={MAX_QUERY}
          aria-required="true"
          aria-invalid={missing || undefined}
          aria-describedby="query-hint query-count"
          placeholder="In English or Hindi"
          className={FIELD_CLASS}
        />
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <button
            ref={submitRef}
            type="submit"
            aria-disabled={loading || undefined}
            className={`${BUTTON_CLASS} aria-disabled:cursor-progress aria-disabled:bg-ledger aria-disabled:text-muted aria-disabled:hover:bg-ledger`}
          >
            {loading ? "Thinking…" : "Ask"}
          </button>
          {/* Always in the page so a screen reader announces the text when it appears. */}
          <p id="query-hint" role="status" className="font-medium">
            {missing ? "Type your question first, in English or Hindi." : ""}
          </p>
          <p id="query-count" className="ml-auto text-sm text-muted tabular-nums">
            {left <= COUNT_FROM ? `${left} ${left === 1 ? "character" : "characters"} left` : ""}
          </p>
        </div>
      </form>

      {/* Tells a screen reader the reply has arrived, as the Stages that were being read go. */}
      <p role="status" className="sr-only">
        {result?.response_type === "answer"
          ? "Your answer is ready."
          : result
            ? "LegalLens could not answer that question."
            : ""}
      </p>

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
          {current?.unauthorized && isSignedIn === false ? (
            <SignInButton>
              <button type="button" className={BUTTON_CLASS}>
                Sign in
              </button>
            </SignInButton>
          ) : (
            <button type="button" onClick={tryAgain} className={BUTTON_CLASS}>
              Try again
            </button>
          )}
        </div>
      )}

      {result?.response_type === "refusal" && (
        <Refusal
          key={`${asked?.q}-${result.refusal_reason}`}
          result={result}
          query={asked?.q ?? ""}
          onReformulate={fillAskBox}
        />
      )}

      {result?.response_type === "answer" && (
        <Answer key={`${asked?.q}-${result.answer}`} result={result} query={asked?.q ?? ""} />
      )}

      <footer className="flex flex-col items-start gap-6 border-t border-rule pt-6">
        {result && (
          <button type="button" onClick={askAnother} className={BUTTON_CLASS}>
            Ask another question
          </button>
        )}
        {/* An answer carries its own, beside its text. */}
        {result?.response_type !== "answer" && (
          <p role="note" className="measure text-sm text-muted">
            {DISCLAIMER}
          </p>
        )}
      </footer>
    </main>
  );
}
