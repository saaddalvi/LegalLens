"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect, useEffectEvent, useLayoutEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { Answer, prefersReducedMotion, Refusal } from "../../answer-view";
import { BUTTON_CLASS } from "../../ask-box";
import type { Stage } from "../../stage-list";
import StageList from "../../stage-list";
import { API_URL } from "@/lib/api-url";
import { detectedLang, errorMessage } from "@/lib/ask-stream";
import { dailyCapMessage, isDailyCap, retryAfterSeconds } from "@/lib/daily-cap";
import type { ContractAnswer, ConversationRef, ConversationTurn } from "@/lib/contract-types";
import { readEvents } from "@/lib/sse";
import { conversationHref } from "./conversation-address";
import QuestionBox from "./question-box";
import type { Starter } from "./starter-questions";

const MISSING = "We could not find that conversation. It may have been deleted.";

// `fresh` marks an answer that arrived while this page was open, which is revealed word by word;
// one loaded with the page is shown at once. `key` stays with a Query from being asked to being
// answered, whatever happens to the turns before it, so its question is never drawn afresh.
type Shown = ConversationTurn & { key: string; fresh: boolean };
type Pending = {
  key: string;
  q: string;
  stages: Stage[];
  error: string | null;
  // The Stage that was running when answering failed, when there was one.
  failedStage: string | null;
};

// One Query and what came of it: the question in a bubble on the right, the reply on the left.
// A `live` turn, asked while this page was open, is given at least the height of the
// conversation's window while it is the latest, so that its question can be scrolled to the top.
function Turn({
  query,
  questionRef,
  latest,
  live,
  children,
}: {
  query: string;
  questionRef: React.RefObject<HTMLParagraphElement | null>;
  latest: boolean;
  live: boolean;
  children: React.ReactNode;
}) {
  return (
    <li
      data-place="the answer"
      className={`flex flex-col gap-5 ${latest && live ? "min-h-[calc(100cqh-1.5rem)]" : ""}`}
    >
      <p
        ref={latest ? questionRef : undefined}
        tabIndex={-1}
        lang={detectedLang(query)}
        className="max-w-[85%] scroll-mt-4 self-end whitespace-pre-wrap break-words rounded-3xl rounded-br-md bg-ledger px-4 py-2.5"
      >
        <span className="sr-only">You asked: </span>
        {query}
      </p>
      {children}
    </li>
  );
}

// The scrolling window onto the conversation, with its column of messages.
function Messages({ scroller, children }: { scroller?: React.Ref<HTMLDivElement>; children: React.ReactNode }) {
  return (
    <div ref={scroller} className="scroll-area @container-size relative min-h-0 flex-1">
      <div className="mx-auto flex min-h-full w-full max-w-2xl flex-col px-4 py-6">{children}</div>
    </div>
  );
}

// The question, with a Clause's heading in the serif the Contract's own words are set in.
function StarterText({ starter: { query, heading } }: { starter: Starter }) {
  if (!heading) return query;
  const at = query.indexOf(`(${heading})`) + 1;
  return (
    <>
      {query.slice(0, at)}
      <span className="font-serif">{heading}</span>
      {query.slice(at + heading.length)}
    </>
  );
}

// The saved Queries and answers of one Contract conversation, and the box for the next Query.
// Without a conversationId the first Query to be answered starts one. Each Query streams its
// Stages as /ask does; a new Query cancels one still being answered, and so does leaving.
export default function ContractConversation({
  contractId,
  conversationId,
  starters = [],
  flaggedCount,
  onReadBrief,
  onSaved,
  onMissing,
  onGone,
  onStartNew,
}: {
  contractId: string;
  // Read once, on arrival: a conversation that gets its id here is not loaded again.
  conversationId?: string;
  // Offered while the conversation is empty.
  starters?: Starter[];
  // How many Clauses the Contract brief flags, and the way to read it, offered there too.
  flaggedCount?: number;
  onReadBrief?: () => void;
  // A Query was answered and saved to this conversation.
  onSaved: (conversation: ConversationRef) => void;
  // The conversation to be loaded is no longer there.
  onMissing: (conversationId: string) => void;
  // A Query found this conversation gone; it carries on as a new one.
  onGone: (conversationId: string) => void;
  onStartNew: () => void;
}) {
  const { getToken } = useAuth();
  // null while a saved conversation's turns are on their way.
  const [turns, setTurns] = useState<Shown[] | null>(() => (conversationId ? null : []));
  // Why the turns could not be loaded. status is null when the service was not reached.
  const [loadError, setLoadError] = useState<{ status: number | null } | null>(null);
  const [loads, setLoads] = useState(0); // counts up on each "Try again"
  const [pending, setPending] = useState<Pending | null>(null);
  const [query, setQuery] = useState("");
  const running = useRef<AbortController | null>(null);
  const conversationIdRef = useRef(conversationId); // set by the backend once one is started
  const latestQuestion = useRef<HTMLParagraphElement>(null);
  const asked = useRef(0); // numbers the Queries asked on this page, for their keys
  const form = useRef<HTMLFormElement>(null);
  const box = useRef<HTMLTextAreaElement>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const opened = useRef(false); // whether a loaded conversation has been moved to its latest turn
  // Tells a screen reader that the reply has arrived, as the Stages that were being read go.
  const [notice, setNotice] = useState("");

  // Leaving, for another conversation or another page, cancels an answer still being written.
  // Next may keep the page left and show it again, so its half-done Stages go too.
  useLayoutEffect(
    () => () => {
      running.current?.abort();
      setPending((p) => (p && p.error === null ? null : p));
    },
    [],
  );

  const unloaded = turns === null;
  const missing = useEffectEvent(onMissing);
  useEffect(() => {
    const saved = conversationIdRef.current;
    if (!unloaded || !saved) return;
    const controller = new AbortController();
    (async () => {
      try {
        const token = await getToken();
        const res = await fetch(
          `${API_URL}${conversationHref(contractId, saved)}`,
          { headers: token ? { Authorization: `Bearer ${token}` } : {}, signal: controller.signal },
        );
        if (controller.signal.aborted) return;
        if (res.status === 404) missing(saved);
        if (!res.ok) return setLoadError({ status: res.status });
        const loaded = (await res.json()) as ConversationTurn[];
        setTurns(loaded.map((t, i) => ({ ...t, key: `saved-${i}`, fresh: false })));
        setLoadError(null);
      } catch {
        if (!controller.signal.aborted) setLoadError({ status: null });
      }
    })();
    return () => controller.abort();
  }, [unloaded, loads, contractId, getToken]);

  // A saved conversation opens on its latest question, as it was left. Only its own window
  // moves, and only once.
  useLayoutEffect(() => {
    const view = scroller.current;
    const question = latestQuestion.current;
    if (opened.current || !conversationId || !view || !question) return;
    opened.current = true;
    view.scrollTop = question.offsetTop - 16;
  }, [conversationId, turns]);

  async function ask(q: string) {
    running.current?.abort(); // a new Query cancels the one in flight
    const controller = new AbortController();
    running.current = controller;
    const current = () => !controller.signal.aborted;
    // A Query tried again keeps the key it failed under.
    const key = pending?.error && pending.q === q ? pending.key : `asked-${++asked.current}`;
    // On the page before it is scrolled to.
    flushSync(() => {
      setPending({ key, q, stages: [], error: null, failedStage: null });
      setNotice("");
    });
    // A starter or "Try again" leaves the page as it is pressed, taking the focus with it.
    if (document.activeElement === document.body) latestQuestion.current?.focus({ preventScroll: true });
    latestQuestion.current?.scrollIntoView?.({
      behavior: prefersReducedMotion() ? "auto" : "smooth",
      block: "start",
    });
    let latest: string | null = null; // the latest Stage to start
    const fail = (message: string) => {
      if (current()) setPending((p) => p && { ...p, error: message, failedStage: latest });
    };
    try {
      // Clerk hands back a fresh token when the cached one is about to expire.
      const token = await getToken();
      const res = await fetch(`${API_URL}/contracts/${encodeURIComponent(contractId)}/ask/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ query: q, conversation_id: conversationIdRef.current }),
        signal: controller.signal,
      });
      if (res.status === 404 && conversationIdRef.current) {
        // Deleted elsewhere, perhaps with its Contract: the next try starts a new one, and says
        // so if it was the Contract.
        onGone(conversationIdRef.current);
        conversationIdRef.current = undefined;
        setTurns([]);
        return fail(`${MISSING} Try again to start a new one.`);
      }
      if (!res.ok) {
        return fail(
          res.status === 404
            ? "We could not find that Contract. It may have been deleted."
            : res.status === 429 && isDailyCap(res)
              ? dailyCapMessage("questions about Contracts", "You can ask again", retryAfterSeconds(res))
              : errorMessage(res.status),
        );
      }
      if (!res.body) return fail(errorMessage(null));
      let finished = false;
      await readEvents(res.body, (name, data) => {
        if (!current()) return;
        if (name === "stage") {
          latest = (data as Stage).id;
          setPending((p) => p && { ...p, stages: [...p.stages, data as Stage] });
        } else if (name === "conversation") {
          conversationIdRef.current = (data as ConversationRef).id;
          onSaved(data as ConversationRef);
        } else if (name === "answer") {
          finished = true;
          answered({ key, query: q, response: data as ContractAnswer, fresh: true });
        } else if (name === "error") {
          finished = true;
          fail(errorMessage(503));
        }
      });
      if (!finished) fail(errorMessage(null));
    } catch {
      fail(errorMessage(null));
    }
  }

  function answered(turn: Shown) {
    flushSync(() => {
      setTurns((t) => [...(t ?? []), turn]);
      setPending(null);
      setNotice(
        turn.response.response_type === "refusal"
          ? "LegalLens could not answer that question."
          : "Your answer is ready.",
      );
    });
    // Focus comes back to the box for the next Query, unless the reader has moved elsewhere.
    const focused = document.activeElement;
    if (focused === document.body || focused === latestQuestion.current || form.current?.contains(focused))
      box.current?.focus({ preventScroll: true });
  }

  // A question offered by a refusal is put in the box, ready to be sent.
  function reformulate(q: string) {
    setQuery(q);
    box.current?.focus({ preventScroll: true });
  }

  function send() {
    const q = query.trim();
    if (!q) return;
    setQuery("");
    void ask(q);
  }

  const loading = pending !== null && pending.error === null;
  if (loadError) {
    const gone = loadError.status === 404;
    function retry() {
      setLoadError(null);
      setLoads((n) => n + 1);
    }
    return (
      <Messages>
        <div role="alert" className="flex flex-col items-start gap-3 border-l-2 border-redtape pl-4">
          <p className="text-redtape">{gone ? MISSING : errorMessage(loadError.status)}</p>
          <button type="button" onClick={gone ? onStartNew : retry} className={BUTTON_CLASS}>
            {gone ? "Start a new conversation" : "Try again"}
          </button>
        </div>
      </Messages>
    );
  }
  if (turns === null)
    return (
      <Messages>
        <p className="text-muted">Loading…</p>
      </Messages>
    );
  return (
    <>
      <Messages scroller={scroller}>
      {turns.length === 0 && !pending && (
        <div className="my-auto flex flex-col gap-4">
          <p className="condensed text-balance text-3xl">What do you want to know about this Contract?</p>
          <p className="measure text-muted">
            Your first question starts a new conversation, answered without your other conversations.
          </p>
          {starters.length > 0 && (
            <ul aria-label="Questions to start with" className="flex flex-col items-start gap-2">
              {starters.map((s) => (
                <li key={s.query}>
                  <button
                    type="button"
                    lang="en"
                    onClick={() => void ask(s.query)}
                    className="min-h-11 break-words rounded-3xl border border-rule px-4 py-2 text-left hover:border-ink hover:bg-ledger"
                  >
                    <StarterText starter={s} />
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div className="flex flex-wrap items-center gap-x-5">
            {onReadBrief && (
              <button type="button" onClick={onReadBrief} className="min-h-11 text-left underline underline-offset-4">
                {flaggedCount
                  ? `Read the Contract brief (${flaggedCount} Flagged ${flaggedCount === 1 ? "clause" : "clauses"})`
                  : "Read the Contract brief"}
              </button>
            )}
            <button
              type="button"
              lang="hi"
              onClick={() => box.current?.focus()}
              className="min-h-11 text-left underline decoration-rule underline-offset-4 hover:decoration-ink"
            >
              इस Contract के बारे में हिंदी में भी पूछ सकते हैं
            </button>
          </div>
        </div>
      )}

      {(turns.length > 0 || pending) && (
        <ol className="flex flex-col gap-10">
          {/* One list, so a question keeps its place in the page when its answer arrives. */}
          {[
            ...turns.map((t, i) => (
              <Turn key={t.key} query={t.query} questionRef={latestQuestion} latest={!pending && i === turns.length - 1} live={t.fresh}>
                {t.response.response_type === "refusal" ? (
                  <Refusal result={t.response} query={t.query} onReformulate={reformulate} instant={!t.fresh} level={3} />
                ) : (
                  <Answer result={t.response} query={t.query} instant={!t.fresh} scope={`turn-${i}-`} level={3} foldSources />
                )}
              </Turn>
            )),
            pending && (
              <Turn key={pending.key} query={pending.q} questionRef={latestQuestion} latest live>
                {(loading || pending.stages.length > 0) && (
                  <StageList
                    stages={pending.stages}
                    loading={loading}
                    failedStage={pending.failedStage}
                    lang={detectedLang(pending.q)}
                  />
                )}
                {pending.error && (
                  <div role="alert" className="flex flex-col items-start gap-3 border-l-2 border-redtape pl-4">
                    <p className="text-redtape">{pending.error}</p>
                    <button type="button" onClick={() => void ask(pending.q)} className={BUTTON_CLASS}>
                      Try again
                    </button>
                  </div>
                )}
              </Turn>
            ),
          ]}
        </ol>
      )}
      </Messages>

      <p role="status" aria-label="Answer notice" className="sr-only">
        {notice}
      </p>

      <QuestionBox
        value={query}
        onChange={setQuery}
        onSend={send}
        busy={loading}
        formRef={form}
        boxRef={box}
      />
    </>
  );
}
