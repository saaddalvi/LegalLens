// For tests: a /contracts backend holding one Contract and its Contract conversations in
// memory, newest first, as the real one lists them.
import { vi } from "vitest";
import type { ContractAnswer, ConversationTurn } from "@/lib/contract-types";

export const ANSWER: ContractAnswer = {
  response_type: "answer",
  refusal_reason: null,
  suggested_reformulation: null,
  answer: "The deposit is Rs. 1,00,000.",
  answer_language: "en",
  trust_label: "contract",
  citations: [],
  fallback_sources: [],
  clause_references: [],
  redirect_to_ask: false,
};

export const turn = (query: string, text: string): ConversationTurn => ({
  query,
  response: { ...ANSWER, answer: text },
});

export type Conversation = { id: string; turns: ConversationTurn[] };

const enc = new TextEncoder();
export const frame = (name: string, data: unknown) => `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`;

// An SSE response whose frames the test pushes by hand.
export function controlled() {
  let ctrl!: ReadableStreamDefaultController<Uint8Array>;
  const body = new ReadableStream<Uint8Array>({ start: (c) => void (ctrl = c) });
  return {
    res: new Response(body),
    push: (name: string, data: unknown) => ctrl.enqueue(enc.encode(frame(name, data))),
    close: () => ctrl.close(),
  };
}

const json = (body: unknown) => new Response(JSON.stringify(body));

// `newestFirst` are the saved conversations. A Query is answered at once with
// "Answer to: <query>", unless `hold` has queued a stream for the test to drive.
export function fakeBackend(newestFirst: Conversation[] = []) {
  let conversations = newestFirst.map((c) => ({ ...c, turns: [...c.turns] }));
  const held: Response[] = [];
  let started = 0;
  const fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(url).pathname;
    const method = init?.method ?? "GET";
    const one = path.match(/\/conversations\/([^/]+)$/)?.[1];
    if (method === "DELETE" && one) {
      conversations = conversations.filter((c) => c.id !== one);
      return new Response(null, { status: 204 });
    }
    if (one) {
      const found = conversations.find((c) => c.id === one);
      return found ? json(found.turns) : new Response(null, { status: 404 });
    }
    if (path.endsWith("/ask/stream")) {
      const queued = held.shift();
      if (queued) return queued;
      const { query, conversation_id } = JSON.parse(init!.body as string);
      const target = conversation_id
        ? conversations.find((c) => c.id === conversation_id)
        : { id: `new-${++started}`, turns: [] };
      if (!target) return new Response(null, { status: 404 });
      const response = { ...ANSWER, answer: `Answer to: ${query}` };
      target.turns.push({ query, response });
      conversations = [target, ...conversations.filter((c) => c !== target)];
      const named = { id: target.id, title: target.turns[0].query };
      return new Response(frame("conversation", named) + frame("answer", response));
    }
    return json({
      id: "c1",
      title: "Rent agreement",
      created_at: "2026-03-01T10:00:00Z",
      page_count: 1,
      clause_count: 2,
      clauses: [
        { number: "3", heading: "Deposit", text: "3. Deposit" },
        { number: "4", heading: "", text: "4. Refunds follow Clause 3." },
      ],
      brief: null,
      conversations: conversations.map((c) => ({
        id: c.id,
        title: c.turns[0].query,
        created_at: "2026-03-01T10:00:00Z",
        updated_at: "2026-03-01T10:00:00Z",
      })),
    });
  });
  vi.stubGlobal("fetch", fetch);
  return {
    fetch,
    // The next Query gets this response instead of an answer.
    hold: (res: Response) => void held.push(res),
  };
}
