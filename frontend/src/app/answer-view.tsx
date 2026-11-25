"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ProvisionNotes, ReplacesNote, STATUS_TEXT } from "./provision-notes";
import { ClauseQuote } from "./clause-quote";
import Stamp from "./stamp";
import { TRUST_EXPLANATION, TRUST_NEEDS_EXPLANATION } from "@/lib/trust-labels";
import { answerAsText } from "@/lib/answer-text";
import type { AskResponse, Citation } from "@/lib/ask-types";
import type { ClauseReference } from "@/lib/contract-types";
import { lawHref } from "@/lib/corpus";
import { provisionKey, splitMentions } from "@/lib/mentions";

// `scope` keeps the ids of two answers on one page apart (a Contract conversation has several).
export const cardId = (c: { act: string; number: string }, scope = "") =>
  `${scope}citation-${c.act}-${c.number}`.replace(/\W+/g, "-");

function CitationCard({
  c,
  open,
  onToggle,
  scope,
}: {
  c: Citation;
  open: boolean;
  onToggle: () => void;
  scope: string;
}) {
  const panelId = `${cardId(c, scope)}-text`;
  // The violet rule says this Provision was checked against the Corpus; a
  // repealed one is ruled in red instead, as struck out.
  const rule = c.status === "repealed" ? "border-redtape" : "border-stamp";
  return (
    <article id={cardId(c, scope)} className={`flex flex-col gap-2 border-l-2 ${rule} pl-4`}>
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
      <ProvisionNotes provision={c} />
      <Link
        href={lawHref(c.act, c.number)}
        aria-label={`Open full Provision: ${c.act}, ${c.number}`}
        className="self-start text-sm text-muted underline underline-offset-4 hover:text-ink"
      >
        Open full Provision
      </Link>
      {open && (
        <div id={panelId} className="flex flex-col gap-2 pb-1">
          {c.supersedes && <ReplacesNote supersedes={c.supersedes} />}
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
const REVEAL_MS = 800;
const FADE_MS = 200;
const MAX_WORD_DELAY_MS = 50;

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
function useReveal(text: string, startInstant = false) {
  const [reduced] = useState(prefersReducedMotion);
  const [finished, setFinished] = useState(false);
  const [skipped, setSkipped] = useState(startInstant);
  const count = paragraphsOf(text).reduce((n, p) => n + wordsOf(p).length, 0);
  const delay = Math.min(MAX_WORD_DELAY_MS, (REVEAL_MS - FADE_MS) / Math.max(count - 1, 1));
  const total = Math.max(count - 1, 0) * delay + FADE_MS;
  useEffect(() => {
    if (reduced) return;
    const t = setTimeout(() => setFinished(true), total);
    return () => clearTimeout(t);
  }, [reduced, total]);
  const instant = reduced || skipped;
  // Escape ends the reveal for keyboard readers, as a click does for pointers.
  useEffect(() => {
    if (instant || finished) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSkipped(true);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [instant, finished]);
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

// `instant` shows an answer already read (one reloaded from a Contract conversation) with no
// reveal. `scope` is a prefix for the element ids of this answer's Citation cards.
export function Answer({
  result,
  instant: shownAtOnce = false,
  scope = "",
}: {
  result: AskResponse & { clause_references?: ClauseReference[] };
  instant?: boolean;
  scope?: string;
}) {
  const { delay, instant, settled, skip } = useReveal(result.answer, shownAtOnce);
  const clauseReferences = result.clause_references ?? [];
  const fade = instant ? "" : "reveal-in";
  const [opened, setOpened] = useState<Set<string>>(new Set());
  // The cards are already on the page once the text has settled, so a chip
  // click opens its card, then scrolls to it and moves focus there.
  const goToCitation = (m: { act: string; number: string }) => {
    setOpened((o) => new Set(o).add(provisionKey(m)));
    const card = document.getElementById(cardId(m, scope));
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
      {/* The Trust label leads: it is known when the answer arrives, and a
          reader should learn how far to trust the text before reading it. */}
      <div className="flex flex-col items-start gap-2">
        <Stamp trust={result.trust_label} press={!shownAtOnce} />
        {TRUST_NEEDS_EXPLANATION.has(result.trust_label) && (
          <p className="max-w-[68ch] text-sm text-muted">{TRUST_EXPLANATION[result.trust_label]}</p>
        )}
      </div>

      {/* Clicking (or Escape) is a shortcut to skip the reveal; reduced motion
          and the finished state need no action, and the text is readable throughout. */}
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
            <CopyAnswer result={result} />
          </div>

          {clauseReferences.length > 0 && (
            <div className={`${fade} flex flex-col gap-5 border-t border-rule pt-6`}>
              <h2 className="condensed text-2xl">From your Contract</h2>
              {clauseReferences.map((r) => (
                <ClauseQuote key={r.number} reference={r} />
              ))}
            </div>
          )}

          {result.citations.length > 0 && (
            <div className={`${fade} flex flex-col gap-5 border-t border-rule pt-6`}>
              <h2 className="condensed text-2xl">Citations</h2>
              {result.citations.map((c) => (
                <CitationCard
                  key={`${c.act}-${c.number}`}
                  c={c}
                  open={opened.has(provisionKey(c))}
                  onToggle={() => toggle(provisionKey(c))}
                  scope={scope}
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

// `instant` shows a refusal already read, with no reveal. `redirect_to_ask` (a Contract
// conversation's refusal of a Query about neither the Contract nor its law) adds a link to /ask.
export function Refusal({
  result,
  onReformulate,
  instant: shownAtOnce = false,
}: {
  result: AskResponse & { redirect_to_ask?: boolean };
  onReformulate: (q: string) => void;
  instant?: boolean;
}) {
  const reason = result.refusal_reason ?? result.answer;
  const { delay, instant, settled, skip } = useReveal(reason, shownAtOnce);
  return (
    <section
      role="status"
      aria-label="Refusal"
      className="flex flex-col gap-3 border border-rule bg-ledger px-4 py-4"
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
      {settled && result.redirect_to_ask && (
        <p className={instant ? "" : "reveal-in"}>
          <Link href="/ask" className="inline-flex min-h-11 items-center underline underline-offset-4">
            Go to the asking screen
          </Link>
        </p>
      )}
    </section>
  );
}
