"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { BUTTON_CLASS, FIELD_CLASS } from "../ask-box";
import Stamp from "../stamp";
import ThemeToggle from "../theme-toggle";
import { DISCLAIMER, answerAsText } from "@/lib/answer-text";
import type { AskResponse, Citation } from "@/lib/ask-types";
import { provisionKey, splitMentions } from "@/lib/mentions";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function detectedLang(q: string): string {
  const letters = [...q].filter((c) => /\p{L}/u.test(c));
  const deva = letters.filter((c) => /[\u0900-\u097F]/.test(c)).length;
  return deva * 2 > letters.length ? "hi" : "en";
}

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

const cardId = (c: { act: string; number: string }) =>
  `citation-${c.act}-${c.number}`.replace(/\W+/g, "-");

function CitationCard({
  c,
  open,
  onToggle,
}: {
  c: Citation;
  open: boolean;
  onToggle: () => void;
}) {
  const panelId = `${cardId(c)}-text`;
  // The violet rule says this Provision was checked against the Corpus; a
  // repealed one is ruled in red instead, as struck out.
  const rule = c.status === "repealed" ? "border-redtape" : "border-stamp";
  return (
    <article id={cardId(c)} className={`flex flex-col gap-2 border-l-2 ${rule} pl-4`}>
      <h3>
        <button
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={onToggle}
          className="flex w-full items-baseline justify-between gap-4 py-1 text-left"
        >
          <span className="min-w-0 break-words">
            <span className={`font-semibold ${c.status === "repealed" ? "line-through decoration-redtape decoration-2" : ""}`}>
              {c.act}, {c.number}
            </span>{" "}
            <span className="text-muted">
              ({c.chapter}, {STATUS_TEXT[c.status]})
            </span>
          </span>
          <span aria-hidden="true" className="shrink-0 text-sm text-muted underline underline-offset-4">
            {open ? "Hide text" : "Show text"}
          </span>
        </button>
      </h3>
      {c.status === "repealed" && (
        <p role="note" className="text-redtape">
          This Provision has been repealed
          {c.superseded_by
            ? `. The current law is ${c.superseded_by.split("; ").join(" and ")}.`
            : "."}
        </p>
      )}
      {c.status === "model" && (
        <p role="note" className="border-l-4 border-warn-border bg-warn-bg px-3 py-2 text-warn">
          This is a model Act, a template that States may adopt. It is not law in force by
          itself. Your State&apos;s own law may differ, so check it.
        </p>
      )}
      {open && (
        <div id={panelId} className="flex flex-col gap-2 pb-1">
          {c.supersedes && (
            <p className="text-muted">
              Replaces {c.supersedes.split("; ").join(" and ")}.
            </p>
          )}
          <blockquote lang="en" className="max-w-[68ch] break-words bg-ledger px-4 py-3 font-serif text-lg leading-relaxed">
            {c.text}
          </blockquote>
        </div>
      )}
    </article>
  );
}

// Reveal timing: the whole reveal finishes within REVEAL_MS however long the
// text is. Short texts use a gentler per-word delay.
const REVEAL_MS = 1500;
const FADE_MS = 300;
const MAX_WORD_DELAY_MS = 80;

function prefersReducedMotion(): boolean {
  return typeof window.matchMedia !== "function"
    || window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

// Splits on whitespace only, so a word is never broken mid-grapheme (Hindi
// included). Trailing whitespace stays with its word.
function wordsOf(paragraph: string): string[] {
  return paragraph.match(/\S+\s*/g) ?? [];
}

function paragraphsOf(text: string): string[] {
  return text.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
}

// Drives one reveal: `settled` once the text is fully shown (so the rest can
// appear), `instant` when nothing should animate (reduced motion, or the
// reader clicked to skip).
function useReveal(text: string) {
  const [reduced] = useState(prefersReducedMotion);
  const [finished, setFinished] = useState(false);
  const [skipped, setSkipped] = useState(false);
  const count = paragraphsOf(text).reduce((n, p) => n + wordsOf(p).length, 0);
  const delay = Math.min(MAX_WORD_DELAY_MS, (REVEAL_MS - FADE_MS) / Math.max(count - 1, 1));
  const total = Math.max(count - 1, 0) * delay + FADE_MS;
  useEffect(() => {
    if (reduced) return;
    const t = setTimeout(() => setFinished(true), total);
    return () => clearTimeout(t);
  }, [reduced, total]);
  const instant = reduced || skipped;
  return { delay, instant, settled: instant || finished, skip: () => {
      // A click that ends a text selection is the reader copying, not skipping.
      if (!window.getSelection()?.toString()) setSkipped(true);
    },
  };
}

// Plain-text paragraphs; while revealing, each word fades in after the last.
// All the text is in the page from the start, so screen readers get it whole.
function RevealedParagraphs({
  text,
  animate,
  delay,
  citations = [],
  onMention,
}: {
  text: string;
  animate: boolean;
  delay: number;
  // When the text has settled, mentions of these Provisions become chips.
  citations?: Citation[];
  onMention?: (c: { act: string; number: string }) => void;
}) {
  let offset = 0; // words in the paragraphs before this one
  return paragraphsOf(text).map((para, i) => {
    const words = wordsOf(para);
    const start = offset;
    offset += words.length;
    return (
      <p key={i} className="whitespace-pre-line">
        {animate
          ? words.map((w, j) => (
              <span
                key={j}
                className="reveal-word"
                style={{ "--reveal-delay": `${(start + j) * delay}ms` } as React.CSSProperties}
              >
                {w}
              </span>
            ))
          : onMention
            ? splitMentions(para, citations).map((seg, j) =>
                "act" in seg ? (
                  <button
                    key={j}
                    type="button"
                    onClick={() => onMention(seg)}
                    className="text-stamp underline decoration-stamp/50 decoration-2 underline-offset-4 hover:decoration-stamp"
                  >
                    {seg.text}
                  </button>
                ) : (
                  seg.text
                ),
              )
            : para}
      </p>
    );
  });
}

type Asked = { q: string };
type Outcome = {
  for: Asked;
  result: AskResponse | null;
  error: string | null;
  // The Stage that was running when answering failed, when there was one.
  failedStage?: string | null;
};
type Stage = { id: string; label: string };
type Progress = { for: Asked; stages: Stage[] };

// Reads a Server-Sent Events body, calling onEvent for each complete frame.
async function readEvents(
  body: ReadableStream<Uint8Array>,
  onEvent: (name: string, data: unknown) => void,
) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const flush = () => {
    let end: number;
    while ((end = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      let name = "message";
      const data: string[] = [];
      for (const line of frame.split("\n")) {
        if (line.startsWith("event:")) name = line.slice(6).trim();
        else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
      }
      if (!data.length) continue; // comment or keepalive
      let parsed: unknown;
      try {
        parsed = JSON.parse(data.join("\n"));
      } catch {
        continue; // skip a malformed frame rather than failing the stream
      }
      onEvent(name, parsed);
    }
  };
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (value) buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, "\n");
      if (done) {
        buffer += "\n\n"; // a body ending without a blank line still has a last frame
        flush();
        return;
      }
      flush();
    }
  } finally {
    reader.cancel().catch(() => {});
  }
}

// Copies the answer, its Citations and the disclaimer as plain text. The outcome
// is announced in a polite live region, which is always on the page so that
// screen readers pick up the message when it appears.
function CopyAnswer({ result }: { result: AskResponse }) {
  const [outcome, setOutcome] = useState<"copied" | "failed" | null>(null);
  useEffect(() => {
    if (!outcome) return;
    const t = setTimeout(() => setOutcome(null), 3000);
    return () => clearTimeout(t);
  }, [outcome]);
  async function copy() {
    try {
      await navigator.clipboard.writeText(answerAsText(result));
      setOutcome("copied");
    } catch {
      // No clipboard (an insecure page) or permission denied.
      setOutcome("failed");
    }
  }
  return (
    <>
      <button
        type="button"
        onClick={copy}
        className="text-sm text-muted underline underline-offset-4 hover:text-ink"
      >
        Copy answer
      </button>
      <span role="status" className="text-sm text-muted">
        {outcome === "copied" ? "Copied" : outcome === "failed" ? "Could not copy" : ""}
      </span>
    </>
  );
}

function Answer({ result }: { result: AskResponse }) {
  const { delay, instant, settled, skip } = useReveal(result.answer);
  const fade = instant ? "" : "reveal-in";
  const [opened, setOpened] = useState<Set<string>>(new Set());
  // The cards are already on the page once the text has settled, so a chip
  // click opens its card, then scrolls to it and moves focus there.
  const goToCitation = (m: { act: string; number: string }) => {
    setOpened((o) => new Set(o).add(provisionKey(m)));
    const card = document.getElementById(cardId(m));
    card?.scrollIntoView?.({ behavior: instant ? "auto" : "smooth", block: "center" });
    card?.querySelector("button")?.focus({ preventScroll: true });
  };
  const toggle = (key: string) =>
    setOpened((o) => {
      const next = new Set(o);
      if (!next.delete(key)) next.add(key);
      return next;
    });
  return (
    <section className="flex flex-col gap-8" aria-label="Answer">
      {/* Clicking is a shortcut for pointer users; reduced motion and the
          finished state need no action, and the text is readable throughout. */}
      <div
        lang={result.answer_language}
        onClick={skip}
        className="flex max-w-[68ch] flex-col gap-5 break-words font-serif text-lg leading-[1.7]"
      >
        <RevealedParagraphs
          text={result.answer}
          animate={!settled}
          delay={delay}
          citations={result.citations}
          onMention={goToCitation}
        />
      </div>

      {settled && (
        <>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 self-start">
            <Stamp trust={result.trust_label} press={!instant} />
            <CopyAnswer result={result} />
          </div>

          {result.citations.length > 0 && (
            <div className={`${fade} flex flex-col gap-5 border-t border-rule pt-6`}>
              <h2 className="condensed text-2xl">Citations</h2>
              {result.citations.map((c) => (
                <CitationCard
                  key={`${c.act}-${c.number}`}
                  c={c}
                  open={opened.has(provisionKey(c))}
                  onToggle={() => toggle(provisionKey(c))}
                />
              ))}
            </div>
          )}

          {result.fallback_sources.length > 0 && (
            <div className={`${fade} flex flex-col gap-3 border-t border-rule pt-6`}>
              <h2 className="condensed text-2xl">Web sources</h2>
              <ul className="flex flex-col break-words">
                {result.fallback_sources.map((s) => (
                  <li key={s.url} className="border-b border-rule py-2">
                    <a href={s.url} className="underline decoration-rule underline-offset-4 hover:decoration-ink">
                      {s.title}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function Refusal({
  result,
  onReformulate,
}: {
  result: AskResponse;
  onReformulate: (q: string) => void;
}) {
  const reason = result.refusal_reason ?? result.answer;
  const { delay, instant, settled, skip } = useReveal(reason);
  return (
    <section
      role="status"
      aria-label="Refusal"
      className="flex flex-col gap-3 border-l-2 border-redtape pl-4"
    >
      <h2 className="condensed text-2xl">LegalLens can&apos;t help with that question</h2>
      <div
        lang={result.answer_language}
        onClick={skip}
        className="flex max-w-[68ch] flex-col gap-3 font-serif text-lg leading-[1.7]"
      >
        <RevealedParagraphs text={reason} animate={!settled} delay={delay} />
      </div>
      {settled && result.suggested_reformulation && (
        <p className={instant ? "" : "reveal-in"}>
          <span className="font-medium">Try asking instead: </span>
          <button
            type="button"
            onClick={() => onReformulate(result.suggested_reformulation ?? "")}
            className="text-left underline underline-offset-4"
          >
            {result.suggested_reformulation}
          </button>
        </p>
      )}
    </section>
  );
}

export default function AskScreen({ initialQuery }: { initialQuery?: string }) {
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery ?? "");
  // The Query being answered. A new object per submission, so asking the same
  // Query again asks again.
  const [asked, setAsked] = useState<Asked | null>(
    initialQuery ? { q: initialQuery } : null,
  );
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [addressQuery, setAddressQuery] = useState(initialQuery);

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
        const res = await fetch(`${API_URL}/ask/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
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
  }, [asked]);

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
      <header className="flex flex-col gap-3 border-b border-rule pt-5 pb-4">
        <div className="flex items-center justify-between gap-4">
          <h1 className="condensed text-2xl">
            <Link href="/">LegalLens</Link>
          </h1>
          <ThemeToggle />
        </div>
        <p role="note" className="text-sm text-muted">
          {DISCLAIMER}
        </p>
      </header>

      <form onSubmit={submit} className="flex flex-col gap-3">
        <label htmlFor="query" className="font-medium">
          Ask a question about Indian law
        </label>
        <textarea
          id="query"
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
        <div role="status" aria-label="Progress">
          {stages.length === 0 && <p className="text-muted">Starting…</p>}
          <ol className="flex flex-col gap-2.5 border-l border-rule">
            {stages.map((stage, i) => {
              const last = i === stages.length - 1;
              const failed = !loading && last && failedStage !== null;
              const active = loading && last;
              return (
                <li
                  key={stage.id}
                  className={`-ml-[5px] flex items-center gap-3 ${
                    failed ? "font-medium text-redtape" : active ? "font-medium text-ink" : "text-muted"
                  }`}
                  aria-current={active ? "step" : undefined}
                >
                  <span
                    aria-hidden="true"
                    className={`size-[9px] shrink-0 rounded-full ${
                      failed ? "bg-redtape" : active ? "stage-pulse bg-ink" : "bg-stamp"
                    }`}
                  />
                  <span lang={detectedLang(asked?.q ?? "")}>{stage.label}</span>
                  <span className="sr-only"> ({failed ? "failed" : active ? "in progress" : "done"})</span>
                  {failed && <span aria-hidden="true" className="text-sm">failed</span>}
                </li>
              );
            })}
          </ol>
        </div>
      )}

      {error && (
        <div role="alert" className="flex flex-col items-start gap-3 border-l-2 border-redtape pl-4">
          <p className="text-redtape">{error}</p>
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
    </main>
  );
}
