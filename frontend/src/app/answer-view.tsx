"use client";

import Link from "next/link";
import { Fragment, useEffect, useId, useState } from "react";
import { flushSync } from "react-dom";
import { BUTTON_CLASS } from "./ask-box";
import CitationCard, { cardId } from "./citation-card";
import { LinkedText } from "./clause-links";
import { ClauseQuote } from "./clause-quote";
import ReturnBar from "./return-bar";
import Stamp from "./stamp";
import { TRUST_EXPLANATION, TRUST_NEEDS_EXPLANATION } from "@/lib/trust-labels";
import { answerAsText, CHECK_YOUR_COPY, DISCLAIMER } from "@/lib/answer-text";
import { askHref, shortProvisionName } from "@/lib/corpus";
import { detectedLang } from "@/lib/ask-stream";
import type { AskResponse, Citation } from "@/lib/ask-types";
import type { ClauseReference } from "@/lib/contract-types";
import { provisionKey, repealedProvisions, splitMentions } from "@/lib/mentions";
import type { ProvisionKey, Repealed } from "@/lib/mentions";

// The level of an answer's own headings: 2 under a page's h1, 3 under a section's h2. The
// lower level is also set smaller than the heading above it.
type Level = 2 | 3;
const HEADING = {
  2: { tag: "h2", card: "h3", size: "text-2xl" },
  3: { tag: "h3", card: "h4", size: "text-xl" },
} as const;

function siteOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

// Reveal timing: the whole reveal finishes within REVEAL_MS however long the
// text is. Short texts use a gentler per-word delay.
const REVEAL_MS = 800;
const FADE_MS = 200;
const MAX_WORD_DELAY_MS = 50;

export function prefersReducedMotion(): boolean {
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
function useReveal(text: string, shownAtOnce = false) {
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
  const instant = reduced || skipped || shownAtOnce;
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

// Follows a mention to its Citation card. `from` is the mention pressed.
type OnMention = (c: ProvisionKey, from: HTMLElement) => void;

// A mention that can be pressed. Not a <button>, which cannot break across lines inside a
// sentence.
function Mention({
  to,
  onMention,
  className,
  children,
}: {
  to: ProvisionKey;
  onMention: OnMention;
  className: string;
  children: React.ReactNode;
}) {
  return (
    <span
      role="button"
      tabIndex={0}
      onClick={(e) => onMention(to, e.currentTarget)}
      onKeyDown={(e) => {
        if (e.key !== "Enter" && e.key !== " ") return;
        e.preventDefault();
        onMention(to, e.currentTarget);
      }}
      className={`cursor-pointer ${className}`}
    >
      {children}
    </span>
  );
}

const IN_FORCE =
  "text-stamp underline decoration-stamp/50 decoration-2 underline-offset-4 hover:decoration-stamp";
const STRUCK = "line-through decoration-redtape decoration-2";

// What LegalLens adds beside a repealed mention, in the answer's language.
const REPEALED_WORDS = {
  en: { repealed: "repealed", now: "now", and: " and " },
  hi: { repealed: "निरस्त", now: "अब", and: " और " },
};

// A repealed Provision named in the answer, struck out. The first time it is named, the law
// that replaced it follows, in the interface's voice so it is not read as the answer's own.
function RepealedMention({
  text,
  provision,
  note,
  language,
  cited,
  onMention,
}: {
  text: string;
  provision: Repealed;
  note: boolean;
  language: string;
  // Keys of the Provisions that have a Citation card to go to.
  cited: Set<string>;
  onMention: OnMention;
}) {
  const words = REPEALED_WORDS[language === "hi" ? "hi" : "en"];
  const struck = <s className={STRUCK}>{text}</s>;
  return (
    <>
      {cited.has(provisionKey(provision)) ? (
        <Mention to={provision} onMention={onMention} className="hover:bg-ledger">
          {struck}
        </Mention>
      ) : (
        struck
      )}
      {note ? (
        <span className="font-sans text-base">
          {" ("}
          <span className="font-medium text-redtape">{words.repealed}</span>
          {provision.replacements.length > 0 && `, ${words.now} `}
          {provision.replacements.map((r, i) => (
            <Fragment key={provisionKey(r)}>
              {i > 0 && words.and}
              {cited.has(provisionKey(r)) ? (
                <Mention to={r} onMention={onMention} className={`whitespace-nowrap ${IN_FORCE}`}>
                  {shortProvisionName(r)}
                </Mention>
              ) : (
                shortProvisionName(r)
              )}
            </Fragment>
          ))}
          {")"}
        </span>
      ) : (
        <span className="sr-only"> ({words.repealed})</span>
      )}
    </>
  );
}

// Plain-text paragraphs; while revealing, each word fades in after the last.
// All the text is in the page from the start, so screen readers get it whole.
function RevealedParagraphs({
  text,
  animate,
  delay,
  citations = [],
  language = "en",
  onMention,
}: {
  text: string;
  animate: boolean;
  delay: number;
  // When the text has settled, mentions of these Provisions become chips, and mentions of
  // repealed ones are struck out.
  citations?: Citation[];
  language?: string;
  onMention?: OnMention;
}) {
  const cited = new Set(citations.map(provisionKey));
  const repealed = repealedProvisions(citations);
  const named = [...citations, ...repealed.values()];
  // Split ahead of drawing, to know where each repealed Provision is named first.
  const paragraphs = paragraphsOf(text).map((para) => ({
    para,
    segments: onMention && !animate ? splitMentions(para, named) : [],
  }));
  const firstNamed = new Map<string, object>();
  for (const seg of paragraphs.flatMap((p) => p.segments)) {
    if ("act" in seg && !firstNamed.has(provisionKey(seg))) firstNamed.set(provisionKey(seg), seg);
  }
  let offset = 0; // words in the paragraphs before this one
  return paragraphs.map(({ para, segments }, i) => {
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
            ? segments.map((seg, j) => {
                if (!("act" in seg)) return <LinkedText key={j} text={seg.text} />;
                const struck = repealed.get(provisionKey(seg));
                return struck ? (
                  <RepealedMention
                    key={j}
                    text={seg.text}
                    provision={struck}
                    note={firstNamed.get(provisionKey(seg)) === seg}
                    language={language}
                    cited={cited}
                    onMention={onMention}
                  />
                ) : (
                  <Mention key={j} to={seg} onMention={onMention} className={IN_FORCE}>
                    {seg.text}
                  </Mention>
                );
              })
            : <LinkedText text={para} />}
      </p>
    );
  });
}

// Copies the question, the answer, what it rests on and the disclaimer as plain text. The outcome
// is announced in a polite live region, which is always on the page so that
// screen readers pick up the message when it appears.
function CopyAnswer({ result, query }: { result: AskResponse; query: string }) {
  const [outcome, setOutcome] = useState<"copied" | "failed" | null>(null);
  useEffect(() => {
    if (!outcome) return;
    const t = setTimeout(() => setOutcome(null), 3000);
    return () => clearTimeout(t);
  }, [outcome]);
  async function copy() {
    try {
      await navigator.clipboard.writeText(
        answerAsText(result, { query, origin: window.location.origin }),
      );
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
        className="inline-flex min-h-11 items-center text-sm text-muted underline underline-offset-4 hover:text-ink"
      >
        Copy answer
      </button>
      <span role="status" className="text-sm text-muted">
        {outcome === "copied" ? "Copied" : outcome === "failed" ? "Could not copy" : ""}
      </span>
    </>
  );
}

const plural = (n: number, noun: string) => `${n} ${noun}${n === 1 ? "" : "s"}`;

// What an answer rests on, counted: "1 Clause, 2 Citations".
function sourceCounts(clauses: number, citations: number, web: number): string {
  return [
    clauses > 0 && plural(clauses, "Clause"),
    citations > 0 && plural(citations, "Citation"),
    web > 0 && plural(web, "web source"),
  ]
    .filter(Boolean)
    .join(", ");
}

// `instant` shows an answer already read (a saved one, or one returned to) with no reveal.
// `scope` is a prefix for the element ids of this answer's Citation cards.
// `foldSources` keeps what the answer rests on behind one button until it is asked for.
// `offerReturn` offers the way back after a mention is followed down the page to its card.
export function Answer({
  result,
  query,
  instant: shownAtOnce = false,
  scope = "",
  level = 2,
  foldSources = false,
  offerReturn = false,
}: {
  result: AskResponse & { clause_references?: ClauseReference[] };
  // The Query this answers, which is copied with it.
  query: string;
  instant?: boolean;
  scope?: string;
  level?: Level;
  foldSources?: boolean;
  offerReturn?: boolean;
}) {
  const { tag: Heading, card: cardHeading, size } = HEADING[level];
  const { delay, instant, settled, skip } = useReveal(result.answer, shownAtOnce);
  const clauseReferences = result.clause_references ?? [];
  const fade = instant ? "" : "reveal-in";
  const [opened, setOpened] = useState<Set<string>>(new Set());
  const [unfolded, setUnfolded] = useState(false);
  const sourcesId = useId();
  const counts = sourceCounts(clauseReferences.length, result.citations.length, result.fallback_sources.length);
  // A repealed Provision is said so even while its card is folded away.
  const repealed = result.citations.filter((c) => c.status === "repealed").length;
  // The mention that was followed to a card, while there is a way back to it.
  const [jump, setJump] = useState<{ key: string; from: HTMLElement } | null>(null);
  const scrolling: ScrollBehavior = instant ? "auto" : "smooth";
  // The cards are already on the page once the text has settled, so a chip click opens its
  // card, then scrolls to it and moves focus there. The card is opened first, so the scroll
  // is measured against its full height, and its heading lands at the top of the screen.
  const goToCitation: OnMention = (m, from) => {
    flushSync(() => {
      setUnfolded(true);
      setOpened((o) => new Set(o).add(provisionKey(m)));
      if (offerReturn) setJump({ key: provisionKey(m), from });
    });
    const card = document.getElementById(cardId(m, scope));
    card?.scrollIntoView?.({ behavior: scrolling, block: "start" });
    card?.querySelector("button")?.focus({ preventScroll: true });
  };
  const goBack = () => {
    if (!jump) return;
    flushSync(() => setJump(null));
    jump.from.scrollIntoView?.({ behavior: scrolling, block: "center" });
    jump.from.focus({ preventScroll: true });
  };
  // The bar goes away with the button pressed, so focus returns to the card it sat in.
  const stay = (c: Citation) => {
    flushSync(() => setJump(null));
    document.getElementById(cardId(c, scope))?.querySelector("button")?.focus({ preventScroll: true });
  };
  const toggle = (key: string) =>
    setOpened((o) => {
      const next = new Set(o);
      if (!next.delete(key)) next.add(key);
      return next;
    });
  return (
    <section className={`flex flex-col ${foldSources ? "gap-5" : "gap-8"}`} aria-label="Answer">
      <Heading className="sr-only">Answer</Heading>
      {/* The Trust label leads: it is known when the answer arrives, and a
          reader should learn how far to trust the text before reading it. */}
      <div className="flex flex-col items-start gap-2">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <Stamp trust={result.trust_label} press={!shownAtOnce} />
          {/* The check is that each cited Provision is in the Corpus, and no more. */}
          {result.citations.length > 0 && (
            <p className="text-sm text-muted">
              {plural(result.citations.length, "Citation")} checked against the statute text
            </p>
          )}
        </div>
        {TRUST_NEEDS_EXPLANATION.has(result.trust_label) && (
          <p className="measure text-sm text-muted">{TRUST_EXPLANATION[result.trust_label]}</p>
        )}
      </div>

      {/* Clicking (or Escape) is a shortcut to skip the reveal; reduced motion
          and the finished state need no action, and the text is readable throughout. */}
      <div
        lang={result.answer_language}
        onClick={skip}
        className="flex measure flex-col gap-5 break-words font-serif text-lg leading-[1.7]"
      >
        <RevealedParagraphs
          text={result.answer}
          animate={!settled}
          delay={delay}
          citations={result.citations}
          language={result.answer_language}
          onMention={goToCitation}
        />
      </div>

      {/* Held close to the answer it qualifies. */}
      <div className={`${foldSources ? "-mt-2" : "-mt-4"} flex flex-col items-start ${foldSources ? "gap-2" : "gap-1"}`}>
        <p role="note" className="measure text-sm text-muted">
          {DISCLAIMER}
        </p>
        {settled && (
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
            {foldSources && counts && (
              <button
                type="button"
                aria-expanded={unfolded}
                aria-controls={sourcesId}
                onClick={() => setUnfolded((u) => !u)}
                className="inline-flex min-h-11 items-center gap-2 rounded-3xl border border-rule px-4 py-2 text-left text-sm font-medium hover:border-ink"
              >
                <svg
                  aria-hidden="true"
                  viewBox="0 0 16 16"
                  className={`size-3.5 shrink-0 ${unfolded ? "rotate-90" : ""}`}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.75"
                >
                  <path d="M6 3.5 10.5 8 6 12.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>
                  Sources: {counts}
                  {repealed > 0 && <span className="text-redtape"> ({repealed} repealed)</span>}
                </span>
              </button>
            )}
            <CopyAnswer result={result} query={query} />
          </div>
        )}
      </div>

      {settled && (
        <div id={sourcesId} hidden={foldSources && !unfolded} className={foldSources && !unfolded ? "" : "contents"}>
          {clauseReferences.length > 0 && (
            <div className={`${fade} flex flex-col gap-5 border-t border-rule pt-6`}>
              <Heading className={`condensed ${size}`}>From your Contract</Heading>
              <p className="-mt-3 measure text-sm text-muted">{CHECK_YOUR_COPY}</p>
              {clauseReferences.map((r) => (
                <ClauseQuote key={r.number} reference={r} />
              ))}
            </div>
          )}

          {result.citations.length > 0 && (
            <div className={`${fade} flex flex-col gap-5 border-t border-rule pt-6`}>
              <Heading className={`condensed ${size}`}>Citations</Heading>
              {result.citations.map((c) => (
                <CitationCard
                  key={`${c.act}-${c.number}`}
                  c={c}
                  open={opened.has(provisionKey(c))}
                  onToggle={() => toggle(provisionKey(c))}
                  scope={scope}
                  heading={cardHeading}
                  wayBack={
                    jump?.key === provisionKey(c) && (
                      <ReturnBar label="answer" onBack={goBack} onStay={() => stay(c)} />
                    )
                  }
                />
              ))}
            </div>
          )}

          {result.fallback_sources.length > 0 && (
            <div className={`${fade} flex flex-col gap-3 border-t border-rule pt-6`}>
              <Heading className={`condensed ${size}`}>Web sources</Heading>
              <ul className="flex flex-col break-words">
                {result.fallback_sources.map((s) => (
                  <li key={s.url} className="flex flex-col items-start border-b border-rule pb-2 last:border-b-0">
                    <a href={s.url} className="measure inline-flex min-h-11 items-center underline decoration-rule underline-offset-4 hover:decoration-ink">
                      {s.title}
                    </a>
                    {/* The site, so a reader can judge it before opening it. */}
                    <span className="text-sm text-muted">{siteOf(s.url)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

// `instant` shows a refusal already read, with no reveal. `asksSuggestion` says `onSuggestion`
// asks the suggested question straight away; without it, pressing the question puts it in an
// ask box to be sent. `redirect_to_ask` (a Contract
// conversation's refusal of a Query about neither the Contract nor its law) adds a link that
// asks that Query on the asking screen.
export function Refusal({
  result,
  query,
  onSuggestion,
  asksSuggestion = false,
  instant: shownAtOnce = false,
  level = 2,
}: {
  result: AskResponse & { redirect_to_ask?: boolean };
  // The Query that was refused.
  query: string;
  onSuggestion: (q: string) => void;
  asksSuggestion?: boolean;
  instant?: boolean;
  level?: Level;
}) {
  const { tag: Heading, size } = HEADING[level];
  const reason = result.refusal_reason ?? result.answer;
  const { delay, instant, settled, skip } = useReveal(reason, shownAtOnce);
  const suggestion = result.suggested_reformulation;
  const suggestionId = useId();
  const fadeIn = instant ? "" : "reveal-in";
  return (
    <section
      role="status"
      aria-label="Refusal"
      className="flex flex-col gap-3 border border-rule bg-ledger px-4 py-4"
    >
      <Heading className={`condensed ${size}`}>LegalLens can&apos;t help with that question</Heading>
      <div
        lang={result.answer_language}
        onClick={skip}
        className="flex measure flex-col gap-3 font-serif text-lg leading-[1.7]"
      >
        <RevealedParagraphs text={reason} animate={!settled} delay={delay} />
      </div>
      {settled &&
        suggestion &&
        (asksSuggestion ? (
          <div className={`flex flex-col items-start gap-2 border-t border-rule pt-3 ${fadeIn}`}>
            <p className="font-medium">Suggested question</p>
            <p
              id={suggestionId}
              lang={detectedLang(suggestion)}
              className="measure break-words font-serif text-lg leading-[1.7]"
            >
              {suggestion}
            </p>
            <button
              type="button"
              aria-describedby={suggestionId}
              onClick={() => onSuggestion(suggestion)}
              className={BUTTON_CLASS}
            >
              Ask this instead
            </button>
          </div>
        ) : (
          <p className={`measure ${fadeIn}`}>
            <span className="font-medium">Try asking instead: </span>
            <button
              type="button"
              lang={detectedLang(suggestion)}
              onClick={() => onSuggestion(suggestion)}
              className="min-h-11 text-left underline underline-offset-4"
            >
              {suggestion}
            </button>
          </p>
        ))}
      {settled && result.redirect_to_ask && (
        <p className={fadeIn}>
          <Link href={askHref(query)} className="inline-flex min-h-11 items-center underline underline-offset-4">
            Ask this on the Ask a question page
          </Link>
        </p>
      )}
    </section>
  );
}
