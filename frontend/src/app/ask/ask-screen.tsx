"use client";

import { SignInButton, useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect, useLayoutEffect, useRef, useState, useSyncExternalStore } from "react";
import { flushSync } from "react-dom";
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
import { keepAnswer, keptAnswer } from "@/lib/kept-answers";
import { readEvents } from "@/lib/sse";

// The longest Query the backend accepts, and how close to it the count of what is left shows.
const MAX_QUERY = 2000;
const COUNT_FROM = 200;

// What a repeat says when it brings back nothing to put in place of the answer already shown.
const NOTHING_NEW = "This time LegalLens found no source it could stand behind.";
const EARLIER_STANDS = "Your earlier answer is still shown below.";

// One attempt to answer a Query. `again` marks one the reader asked for, which is sent even
// when an answer to that Query is already kept.
type Asked = { q: string; again: boolean };
type Outcome = {
  for: Asked;
  error: string | null;
  // The service refused the session token.
  unauthorized?: boolean;
  // The Stage that was running when answering failed, when there was one.
  failedStage?: string | null;
  // The answer arrived while the page was being read, so it is revealed word by word.
  fresh?: boolean;
};
type Progress = { for: Asked; stages: Stage[] };

const fromAddress = (q?: string): Asked | null => (q ? { q, again: false } : null);

// The reply that says no source supports an answer, which a temporary outage can cause.
const foundNothing = (r: AskResponse) => r.response_type === "answer" && r.trust_label === "none";

const QUIET_BUTTON_CLASS =
  "inline-flex min-h-11 min-w-11 shrink-0 items-center justify-center text-sm text-muted underline underline-offset-4 hover:text-ink";

// Kept answers change only here, followed by a state change that draws them.
const subscribe = () => () => {};

export default function AskScreen({ initialQuery }: { initialQuery?: string }) {
  const router = useRouter();
  const { getToken, isLoaded, isSignedIn, userId } = useAuth();
  // Whose answers these are. It stays when a session ends, so what is shown stays too.
  const [owner, setOwner] = useState(userId ?? "");
  const [query, setQuery] = useState(initialQuery ?? "");
  // The Query being answered. A new object per attempt.
  const [asked, setAsked] = useState(() => fromAddress(initialQuery));
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [addressQuery, setAddressQuery] = useState(initialQuery);
  const [missing, setMissing] = useState(false);
  // Once a Query is asked the form folds to the question, until the reader wants it back.
  const [editing, setEditing] = useState(false);
  const questionRef = useRef<HTMLHeadingElement>(null);
  const editRef = useRef<HTMLButtonElement>(null);
  const fieldRef = useRef<HTMLTextAreaElement>(null);
  const submitRef = useRef<HTMLButtonElement>(null);
  // The last attempt that came to an end, with an answer or an error.
  const settled = useRef<Asked | null>(null);

  // The address is the source of truth: when it changes to another Query (a
  // link, back or forward), the ask box shows that Query and its answer, unless
  // this screen is already answering it.
  if (initialQuery !== addressQuery) {
    setAddressQuery(initialQuery);
    setQuery(initialQuery ?? "");
    setMissing(false);
    if (initialQuery !== asked?.q) {
      setEditing(false);
      setAsked(fromAddress(initialQuery));
    }
  }

  if (userId && userId !== owner) {
    setOwner(userId);
    // Someone else has signed in, and Next may have kept this page: start from the address.
    if (owner) {
      setQuery(initialQuery ?? "");
      setMissing(false);
      setEditing(false);
      setAsked(fromAddress(initialQuery));
    }
  }

  // Next may keep a page that is left and show it again. An answer shown then is not revealed
  // afresh, and the Stages of an unfinished attempt go, as it starts over.
  useLayoutEffect(
    () => () => {
      setOutcome((o) => o && { ...o, fresh: false });
      setProgress((p) => (p && p.for === settled.current ? p : null));
    },
    [],
  );

  // Sends the Query, unless this attempt has already ended or a kept answer stands in for it.
  // Leaving cancels an attempt in flight, and showing the page again restarts it.
  useEffect(() => {
    if (!asked || !isLoaded || settled.current === asked) return;
    if (!asked.again && keptAnswer(owner, asked.q)) return;
    const controller = new AbortController();
    const stages: Stage[] = [];
    let running: string | null = null; // the latest Stage to start
    const settle = (end: Omit<Outcome, "for">) => {
      if (controller.signal.aborted) return;
      settled.current = asked;
      setOutcome({ for: asked, ...end });
    };
    const fail = (error: string, failedStage: string | null = null) => settle({ error, failedStage });
    const answered = (result: AskResponse) => {
      if (controller.signal.aborted) return;
      const earlier = keptAnswer(owner, asked.q);
      if (earlier && !foundNothing(earlier) && foundNothing(result)) return fail(NOTHING_NEW);
      keepAnswer(owner, asked.q, result);
      settle({ error: null, fresh: true });
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
          const error = errorMessage(res.status, retryAfterSeconds(res));
          return settle({ error, unauthorized: res.status === 401 });
        }
        if (!res.body) return fail(errorMessage(null));
        let finished = false;
        await readEvents(res.body, (name, data) => {
          if (controller.signal.aborted) return;
          if (name === "stage") {
            running = (data as Stage).id;
            stages.push(data as Stage);
            setProgress({ for: asked, stages: [...stages] });
          } else if (name === "answer") {
            finished = true;
            answered(data as AskResponse);
          } else if (name === "error") {
            finished = true;
            fail(errorMessage(503), (data as { stage?: string }).stage ?? running);
          }
        });
        if (!finished) fail(errorMessage(null), running);
      } catch {
        fail(errorMessage(null), running);
      }
    })();
    return () => controller.abort();
  }, [asked, isLoaded, owner, getToken]);

  // The answer shown for the Query: the latest that came back for it.
  const result = useSyncExternalStore(
    subscribe,
    () => (asked ? keptAnswer(owner, asked.q) : null),
    () => null,
  );
  const current = outcome?.for === asked ? outcome : null;
  // Until Clerk says who is reading, a kept answer cannot be looked for.
  const waiting = asked !== null && !asked.again && !isLoaded;
  const loading =
    asked !== null && current === null && !waiting && (asked.again || result === null);
  const busy = loading || waiting;
  const error = current?.error ?? null;
  const stages = progress?.for === asked ? progress.stages : [];
  const failedStage = current?.failedStage ?? null;
  const showStages = loading || (error !== null && stages.length > 0);

  const folded = asked !== null && !editing;
  const suggests = result?.response_type === "refusal" && Boolean(result.suggested_reformulation);

  // The button pressed goes away with the error, so focus moves to the question or to Ask.
  function tryAgain() {
    if (!asked) return;
    setAsked({ q: asked.q, again: true });
    (folded ? questionRef : submitRef).current?.focus();
  }

  // Brings the form back and takes the reader to the ask box.
  function openAskBox() {
    flushSync(() => setEditing(true));
    fieldRef.current?.scrollIntoView?.({ block: "center" });
    fieldRef.current?.focus({ preventScroll: true });
  }

  function edit() {
    if (!asked) return;
    setQuery(asked.q);
    openAskBox();
  }

  // Folds the form back to the Query already asked, dropping what was typed over it.
  function cancelEdit() {
    flushSync(() => {
      setQuery(asked?.q ?? "");
      setMissing(false);
      setEditing(false);
    });
    editRef.current?.focus();
  }

  // Starts over: the address drops the Query, which clears the ask box and the answer.
  function askAnother() {
    router.push("/ask", { scroll: false });
    flushSync(() => {
      setAsked(null);
      setQuery("");
      setMissing(false);
    });
    openAskBox();
  }

  // Asks a Query the reader chose here. What they pressed goes away as the form folds, so
  // focus moves to the question it folds to.
  function send(q: string) {
    flushSync(() => {
      setQuery(q);
      setMissing(false);
      setAsked({ q, again: true });
      setEditing(false);
    });
    questionRef.current?.focus();
    if (q !== initialQuery) {
      router.push(`/ask?${new URLSearchParams({ q })}`, { scroll: false });
    }
  }

  function sendSuggestion(q: string) {
    if (!busy) send(q);
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    // The button stays focusable while an answer is being written, so it is checked here.
    if (busy) return;
    const q = query.trim();
    if (!q) {
      setMissing(true);
      fieldRef.current?.focus();
      return;
    }
    send(q);
  }

  const left = MAX_QUERY - query.length;

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-4 pb-16 has-data-return-bar:pb-24 sm:px-8">
      <SiteHeader current="ask" />

      {folded ? (
        // The question steps back to a line or three, so the answer leads.
        <div className="flex items-start justify-between gap-4 border-b border-rule pb-2">
          <h1
            ref={questionRef}
            tabIndex={-1}
            lang={detectedLang(asked.q)}
            className="measure my-2 line-clamp-3 min-w-0 flex-1 whitespace-pre-line break-words font-serif text-xl leading-normal"
          >
            {asked.q}
          </h1>
          <button
            ref={editRef}
            type="button"
            aria-label="Edit question"
            onClick={edit}
            className={QUIET_BUTTON_CLASS}
          >
            Edit
          </button>
        </div>
      ) : (
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
              aria-disabled={busy || undefined}
              className={`${BUTTON_CLASS} aria-disabled:cursor-progress aria-disabled:bg-ledger aria-disabled:text-muted aria-disabled:hover:bg-ledger`}
            >
              {loading ? "Thinking…" : "Ask"}
            </button>
            {asked && (
              <button type="button" onClick={cancelEdit} className={QUIET_BUTTON_CLASS}>
                Cancel
              </button>
            )}
            {/* Always in the page so a screen reader announces the text when it appears. */}
            <p id="query-hint" role="status" className="font-medium">
              {missing ? "Type your question first, in English or Hindi." : ""}
            </p>
            <p id="query-count" className="ml-auto text-sm text-muted tabular-nums">
              {left <= COUNT_FROM ? `${left} ${left === 1 ? "character" : "characters"} left` : ""}
            </p>
          </div>
        </form>
      )}

      {/* Tells a screen reader the reply has arrived, as the Stages that were being read go. */}
      <p role="status" className="sr-only">
        {!result || loading || error
          ? ""
          : result.response_type === "answer"
            ? "Your answer is ready."
            : "LegalLens could not answer that question."}
      </p>

      {waiting && <p className="text-muted">Loading…</p>}

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
          <p>
            {error}
            {result && ` ${EARLIER_STANDS}`}
          </p>
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
          onSuggestion={sendSuggestion}
          asksSuggestion
          instant={!current?.fresh}
        />
      )}

      {result?.response_type === "answer" && (
        <Answer
          key={`${asked?.q}-${result.answer}`}
          result={result}
          query={asked?.q ?? ""}
          instant={!current?.fresh}
          offerReturn
        />
      )}

      <footer className="flex flex-col items-start gap-6 border-t border-rule pt-6">
        {/* A suggested question is the next step where there is one, so this stands back. */}
        {result && (
          <button
            type="button"
            onClick={askAnother}
            className={suggests ? QUIET_BUTTON_CLASS : BUTTON_CLASS}
          >
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
