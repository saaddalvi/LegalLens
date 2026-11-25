"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect, useRef, useState } from "react";
import { Answer, Refusal } from "../../answer-view";
import { BUTTON_CLASS, FIELD_CLASS } from "../../ask-box";
import type { Stage } from "../../stage-list";
import StageList from "../../stage-list";
import { API_URL } from "@/lib/api-url";
import { detectedLang, errorMessage } from "@/lib/ask-stream";
import { dailyCapMessage, isDailyCap, retryAfterSeconds } from "@/lib/daily-cap";
import type { ContractAnswer, ConversationRef, ConversationTurn } from "@/lib/contract-types";
import { readEvents } from "@/lib/sse";

// `fresh` marks an answer that arrived while this page was open, which is revealed word by word;
// one loaded with the page is shown at once.
type Shown = ConversationTurn & { fresh: boolean };
type Pending = {
  q: string;
  stages: Stage[];
  error: string | null;
  // The Stage that was running when answering failed, when there was one.
  failedStage: string | null;
};

// The saved Queries and answers of one Contract conversation, and the box for the next Query.
// Without a conversationId the first Query to be answered starts one. Each Query streams its
// Stages as /ask does; a new Query cancels one still being answered.
export default function ContractConversation({
  contractId,
  conversationId,
  initial,
}: {
  contractId: string;
  conversationId?: string;
  initial: ConversationTurn[];
}) {
  const { getToken } = useAuth();
  const [turns, setTurns] = useState<Shown[]>(() => initial.map((t) => ({ ...t, fresh: false })));
  const [pending, setPending] = useState<Pending | null>(null);
  const [query, setQuery] = useState("");
  const running = useRef<AbortController | null>(null);
  const conversationIdRef = useRef(conversationId); // set by the backend once one is started

  useEffect(() => () => running.current?.abort(), []);

  async function ask(q: string) {
    running.current?.abort(); // a new Query cancels the one in flight
    const controller = new AbortController();
    running.current = controller;
    const current = () => !controller.signal.aborted;
    setPending({ q, stages: [], error: null, failedStage: null });
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
        conversationIdRef.current = undefined;
        setTurns([]);
        return fail("We could not find that conversation. It may have been deleted. Try again to start a new one.");
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
        } else if (name === "answer") {
          finished = true;
          setTurns((t) => [...t, { query: q, response: data as ContractAnswer, fresh: true }]);
          setPending(null);
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

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    setQuery("");
    void ask(q);
  }

  const loading = pending !== null && pending.error === null;
  return (
    <section id="ask" aria-labelledby="conversation" className="flex scroll-mt-4 flex-col gap-8">
      <h2 id="conversation" tabIndex={-1} data-jump-focus className="condensed self-start text-2xl">
        Ask about this Contract
      </h2>

      {turns.length > 0 && (
        <ol className="flex flex-col gap-10">
          {turns.map((t, i) => (
            <li key={i} data-place="the answer" className="flex flex-col gap-5">
              <p lang={detectedLang(t.query)} className="measure break-words border-b border-rule pb-2 font-medium">
                <span className="sr-only">You asked: </span>
                {t.query}
              </p>
              {t.response.response_type === "refusal" ? (
                <Refusal result={t.response} query={t.query} onReformulate={setQuery} instant={!t.fresh} level={3} />
              ) : (
                <Answer result={t.response} query={t.query} instant={!t.fresh} scope={`turn-${i}-`} level={3} />
              )}
            </li>
          ))}
        </ol>
      )}

      {pending && (
        <div className="flex flex-col gap-5">
          <p lang={detectedLang(pending.q)} className="measure break-words border-b border-rule pb-2 font-medium">
            <span className="sr-only">You asked: </span>
            {pending.q}
          </p>
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
        </div>
      )}

      <form onSubmit={submit} className="flex flex-col gap-3">
        {/* The heading above already says it on screen. */}
        <label htmlFor="contract-query" className="sr-only">
          Ask a question about this Contract
        </label>
        <textarea
          id="contract-query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          rows={3}
          placeholder="In English or Hindi"
          className={FIELD_CLASS}
        />
        <button type="submit" className={`${BUTTON_CLASS} self-start`}>
          {loading ? "Ask this instead" : "Ask"}
        </button>
      </form>
    </section>
  );
}
