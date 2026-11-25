"use client";

import { createContext, Fragment, useContext, useEffect, useEffectEvent, useState } from "react";
import { flushSync } from "react-dom";
import { BUTTON_CLASS } from "./ask-box";

// Every Clause number on a Contract's page is a link to that Clause. Following one marks the
// Clause and offers the way back, by a button or the browser's own Back. Outside <ClauseJumps>
// (the asking screen, the landing page) the numbers stay plain text.

export const clauseId = (number: string) => `clause-${number}`;

// A click that asks the browser to open a link elsewhere, and is left to it.
export const isModifiedClick = (e: React.MouseEvent) => e.metaKey || e.ctrlKey || e.shiftKey || e.altKey;

// What a rewrite of the current history entry must keep: whether a Clause link added it.
export const jumpState = () => ({ clauseJump: window.history.state?.clauseJump });

// Scrolls a part of the page to the top and moves focus to its heading.
export function jumpTo(target: HTMLElement) {
  target.scrollIntoView?.({ block: "start" });
  (target.querySelector<HTMLElement>("[data-jump-focus]") ?? target).focus({ preventScroll: true });
}

// `from` is the link that was followed, or null when there is nowhere to go back to.
// `label` names the part of the page it is in.
type Jump = { number: string; from: HTMLElement | null; label: string };

type Jumps = {
  has: (number: string) => boolean;
  jump: Jump | null;
  go: (number: string, from: HTMLElement) => void;
  goBack: () => void;
  stay: () => void;
};

const Context = createContext<Jumps | null>(null);

export default function ClauseJumps({
  numbers,
  view,
  onReveal,
  children,
}: {
  numbers: string[];
  // Changes when the page shows something else, which ends any way back into what it showed.
  view?: number;
  // Brings the part of the page holding an element into view, before it is scrolled to or
  // focused. For a page that shows one part at a time.
  onReveal?: (element: HTMLElement) => void;
  children: React.ReactNode;
}) {
  const [jump, setJump] = useState<Jump | null>(null);
  const [seen, setSeen] = useState(view);
  if (view !== seen) {
    setSeen(view);
    setJump(null);
  }

  const reveal = useEffectEvent((element: HTMLElement) => onReveal?.(element));

  function restore(from: HTMLElement) {
    setJump(null);
    onReveal?.(from);
    from.focus({ preventScroll: true });
    // The browser puts the scroll position back itself after Back. Scroll only if it did not.
    requestAnimationFrame(() => {
      const { top, bottom } = from.getBoundingClientRect();
      if (bottom < 0 || top > window.innerHeight) from.scrollIntoView?.({ block: "center" });
    });
  }

  function go(number: string, from: HTMLElement) {
    const target = document.getElementById(clauseId(number));
    if (!target) return;
    // A cross-reference followed from one Clause to another keeps the first starting point.
    const first = jump?.from && from.closest("[data-clause-list]") ? jump : null;
    // One history entry however many Clauses are visited, so Back leads to the start.
    const state = window.history.state;
    window.history[state?.clauseJump ? "replaceState" : "pushState"]({ ...state, clauseJump: true }, "");
    const label = from.closest<HTMLElement>("[data-place]")?.dataset.place ?? "where you were";
    flushSync(() => setJump(first ? { ...first, number } : { number, from, label }));
    onReveal?.(target);
    jumpTo(target);
  }

  function goBack() {
    if (window.history.state?.clauseJump) window.history.back();
    else if (jump?.from) restore(jump.from);
  }

  function stay() {
    if (!jump) return;
    window.history.replaceState({ ...window.history.state, clauseJump: false }, "");
    flushSync(() => setJump({ ...jump, from: null }));
    const target = document.getElementById(clauseId(jump.number));
    target?.querySelector<HTMLElement>("[data-jump-focus]")?.focus({ preventScroll: true });
  }

  const returnTo = useEffectEvent(restore);
  useEffect(() => {
    const from = jump?.from;
    if (!from) return;
    const onPop = () => {
      if (!window.history.state?.clauseJump) returnTo(from);
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, [jump]);

  // A Clause link opened in a new tab arrives before the Contract has loaded, so the browser
  // finds nothing to scroll to.
  useEffect(() => {
    const id = decodeURIComponent(window.location.hash.slice(1));
    const number = numbers.find((n) => clauseId(n) === id);
    const target = number === undefined ? null : document.getElementById(id);
    if (number === undefined || !target) return;
    const frame = requestAnimationFrame(() => {
      setJump({ number, from: null, label: "" });
      reveal(target);
      jumpTo(target);
    });
    return () => cancelAnimationFrame(frame);
    // Once, when the Contract first appears.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const has = (number: string) => numbers.includes(number);
  return <Context.Provider value={{ has, jump, go, goBack, stay }}>{children}</Context.Provider>;
}

export function ClauseLink({
  number,
  className,
  label,
  children,
}: {
  number: string;
  className: string;
  // The accessible name, when the link's text is only the number.
  label?: string;
  children: React.ReactNode;
}) {
  const jumps = useContext(Context);
  if (!jumps?.has(number)) return children;
  return (
    <a
      href={`#${clauseId(number)}`}
      aria-label={label}
      className={className}
      onClick={(e) => {
        if (isModifiedClick(e)) return;
        e.preventDefault();
        jumps.go(number, e.currentTarget);
      }}
    >
      {children}
    </a>
  );
}

const NUMBER = "\\d+(?:\\.\\d+)*(?:\\([a-z]+\\))*";
const JOIN = "(?:\\s*[,&–-]\\s*|\\s+(?:and|or|to|और|तथा)\\s+)";
// "Clause 4.1", "Clauses 2, 3 and 4", "खंड 7(a)". The words for a Provision (Section,
// Article, धारा) are left out: those numbers are the law's, not the Contract's.
const MENTION = new RegExp(
  `(?<!\\w)(clauses?|खंड|क्लॉज़?)\\s+(${NUMBER}(?:${JOIN}${NUMBER})*)`,
  "gi",
);
// "clause 3 of the Consumer Protection Act" is a clause of an Act.
const OF_AN_ACT =
  /^\s+of\s+(?:the\s+)?(?:[A-Z][\w'’-]*,?\s+(?:(?:and|of)\s+)?)*(?:Act|Code|Sanhita|Adhiniyam|Constitution)\b/;

const INLINE_LINK = "underline decoration-muted underline-offset-4 hover:decoration-ink";

// Running text with each mention of one of this Contract's Clauses made a link. `except` is
// the Clause the text belongs to, which has no reason to link to itself.
export function LinkedText({ text, except }: { text: string; except?: string }) {
  const jumps = useContext(Context);
  if (!jumps) return text;
  const parts: React.ReactNode[] = [];
  let pos = 0;
  for (const m of text.matchAll(MENTION)) {
    const [whole, word, list] = m;
    if (OF_AN_ACT.test(text.slice(m.index + whole.length))) continue;
    const listStart = m.index + whole.length - list.length;
    const numbers = [...list.matchAll(new RegExp(NUMBER, "gi"))];
    // After a singular "Clause", a later number is something else ("Clause 4 and 30 days").
    const read = word.toLowerCase() === "clause" ? numbers.slice(0, 1) : numbers;
    read.forEach((n, i) => {
      const number = n[0];
      if (number === except || !jumps.has(number)) return;
      // The first link takes in the word, so it reads "Clause 4.1".
      const start = i === 0 ? m.index : listStart + n.index;
      const end = listStart + n.index + number.length;
      parts.push(
        text.slice(pos, start),
        <ClauseLink
          key={start}
          number={number}
          label={i === 0 ? undefined : `Clause ${number}`}
          className={INLINE_LINK}
        >
          {text.slice(start, end)}
        </ClauseLink>,
      );
      pos = end;
    });
  }
  parts.push(text.slice(pos));
  return parts.map((p, i) => <Fragment key={i}>{p}</Fragment>);
}

// The way back, held at the foot of the screen, clear of the sidebar. It sits just after the Clause's heading in the
// page, so it is also the next stop for the Tab key. A scrolling part of the page that holds it
// keeps clear of it (globals.css).
function ReturnBar({ label, onBack, onStay }: { label: string; onBack: () => void; onStay: () => void }) {
  return (
    <div data-return-bar className="fixed inset-x-0 bottom-0 z-10 lg:left-72 border-t-2 border-ink bg-paper px-4 pb-[env(safe-area-inset-bottom)] sm:px-8">
      <div className="mx-auto flex max-w-[44rem] items-center justify-between gap-3 py-2">
        <button type="button" onClick={onBack} className={`${BUTTON_CLASS} min-h-11 min-w-0`}>
          Back to {label}
        </button>
        <button
          type="button"
          aria-label="Stay here"
          title="Stay here"
          onClick={onStay}
          className="inline-flex size-11 shrink-0 items-center justify-center rounded border border-rule hover:border-ink"
        >
          <svg aria-hidden="true" viewBox="0 0 16 16" className="size-[18px]" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M3.5 3.5l9 9M12.5 3.5l-9 9" strokeLinecap="round" />
          </svg>
        </button>
      </div>
    </div>
  );
}

// A line that reads as a sentence still running: it has a verb of duty, or ends on a comma
// or a word that cannot end a title.
const RUNS_ON = /\b(?:shall|will|must|may)\b|(?:[,;:-]|\b(?:a|an|the|of|to|by|for|in|on|at|with|from|as|is|be|and|or|any))$/i;

// A Clause's heading is the rest of its first line, which its text then repeats. A title is
// shown once, as the heading. A first line that may be the start of a sentence stays in the
// text, with no heading, so that no sentence is cut in two.
export function headingAndBody(heading: string, text: string): { heading: string; body: string } {
  const [first, ...rest] = text.split("\n");
  if (!heading || !first.trim().endsWith(heading)) return { heading: "", body: text };
  const body = rest.join("\n").replace(/^\s*\n/, "");
  // A title is short, and what follows it starts afresh.
  const isTitle =
    !body.trim() ||
    (heading.split(/\s+/).length <= 8 && !RUNS_ON.test(heading) && /^\s*["“'(]?[A-Z(]/.test(body));
  return isTitle ? { heading, body } : { heading: "", body: text };
}

// One Clause of the Contract, verbatim, and the target of every link to its number.
export function ClauseItem({
  number,
  heading: given,
  text,
}: {
  number: string;
  heading: string;
  text: string;
}) {
  const jumps = useContext(Context);
  const jump = jumps?.jump?.number === number ? jumps.jump : null;
  const { heading, body } = headingAndBody(given, text);
  return (
    <li
      id={clauseId(number)}
      data-place={number === "0" ? "the Recitals" : `Clause ${number}`}
      data-current={jump ? "" : undefined}
      className="flex scroll-mt-4 flex-col gap-2 border-l-2 border-ink py-2 pr-3 pl-4 data-current:bg-ledger data-current:outline-2 data-current:outline-ink"
    >
      <h3 tabIndex={-1} data-jump-focus className="self-start font-semibold">
        {number === "0" ? (
          "Recitals and parties"
        ) : (
          <>
            Clause {number}
            {heading && (
              <span className="font-normal text-muted">
                {" · "}
                <span lang="en" className="font-serif">
                  {heading}
                </span>
              </span>
            )}
          </>
        )}
      </h3>
      {jumps && jump?.from && <ReturnBar label={jump.label} onBack={jumps.goBack} onStay={jumps.stay} />}
      {body && (
        <p lang="en" className="measure whitespace-pre-line break-words font-serif text-lg leading-relaxed">
          <LinkedText text={body} except={number} />
        </p>
      )}
    </li>
  );
}
