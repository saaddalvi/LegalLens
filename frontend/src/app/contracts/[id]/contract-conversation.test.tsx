import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import ContractView from "./contract-view";
import ContractConversation from "./contract-conversation";
import type { ContractAnswer, ConversationTurn } from "@/lib/contract-types";

const getToken = vi.fn();
vi.mock("@clerk/nextjs", () => ({ useAuth: () => ({ getToken }) }));

const enc = new TextEncoder();
const frame = (name: string, data: unknown) => `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`;
const stage = (id: string, label: string) => frame("stage", { id, label });

const ANSWER: ContractAnswer = {
  response_type: "answer",
  refusal_reason: null,
  suggested_reformulation: null,
  answer: "The deposit is Rs. 1,00,000.",
  answer_language: "en",
  trust_label: "contract_and_corpus",
  citations: [
    {
      act: "Model Tenancy Act",
      chapter: "Chapter II",
      number: "11",
      status: "model",
      text: "The security deposit shall not exceed two months' rent.",
      superseded_by: null,
      supersedes: null,
    },
  ],
  fallback_sources: [],
  clause_references: [{ number: "3", text: "3. Deposit\nThe Tenant pays Rs. 1,00,000." }],
  redirect_to_ask: false,
};
const answer = (over: Partial<ContractAnswer>): ContractAnswer => ({ ...ANSWER, ...over });

function sseResponse(chunks: string[]) {
  return {
    ok: true,
    status: 200,
    body: new ReadableStream<Uint8Array>({
      start(c) {
        chunks.forEach((t) => c.enqueue(enc.encode(t)));
        c.close();
      },
    }),
  };
}

// A response whose chunks the test pushes by hand.
function controlled() {
  let ctrl!: ReadableStreamDefaultController<Uint8Array>;
  const body = new ReadableStream<Uint8Array>({ start: (c) => (ctrl = c) });
  return {
    res: { ok: true, status: 200, body },
    push: (t: string) => ctrl.enqueue(enc.encode(t)),
    close: () => ctrl.close(),
  };
}

beforeEach(() => getToken.mockResolvedValue("tok"));
afterEach(() => {
  vi.unstubAllGlobals();
  getToken.mockReset();
});

async function typeAndAsk(user: ReturnType<typeof userEvent.setup>, q: string) {
  await user.type(screen.getByLabelText(/ask a question about this contract/i), q);
  await user.click(screen.getByRole("button", { name: /^Ask/ }));
}

const TURNS: ConversationTurn[] = [
  { query: "What is the deposit?", response: ANSWER },
  { query: "And the notice period?", response: answer({ answer: "Two months.", trust_label: "contract", citations: [], clause_references: [{ number: "7.2", text: "7.2 Notice is two months." }] }) },
];

it("shows the saved conversation in order after a reload, with each answer's sources", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        id: "c1",
        title: "Rent agreement",
        created_at: "2026-03-01T10:00:00Z",
        page_count: 1,
        clause_count: 1,
        clauses: [{ number: "3", heading: "Deposit", text: "3. Deposit" }],
        brief: null,
        conversation: TURNS,
      }),
    }),
  );
  render(<ContractView id="c1" />);
  await screen.findByText("The deposit is Rs. 1,00,000.");
  const queries = screen.getAllByText(/^(What is the deposit\?|And the notice period\?)$/).map((e) => e.textContent);
  expect(queries).toEqual(["You asked: What is the deposit?", "You asked: And the notice period?"]);
  // Answers are shown at once (no reveal), each with its Trust label and Clause reference.
  expect(screen.getByText("The deposit is Rs. 1,00,000.")).toBeInTheDocument();
  expect(screen.getByText("Two months.")).toBeInTheDocument();
  expect([...document.querySelectorAll("[data-trust]")].map((e) => [e.getAttribute("data-trust"), e.textContent])).toEqual([
    ["contract_and_corpus", "From your Contract and statute text"],
    ["contract", "From your Contract"],
  ]);
  expect(screen.getByText("Your Contract, Clause 3")).toBeInTheDocument();
  expect(screen.getByText("Your Contract, Clause 7.2")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Open full Provision: Model Tenancy Act, 11/ })).toHaveAttribute(
    "href",
    "/law/Model%20Tenancy%20Act/11",
  );
});

it("streams the Stages of each Query, then shows its answer", async () => {
  const user = userEvent.setup();
  const first = controlled();
  const second = controlled();
  const fetchFn = vi.fn().mockResolvedValueOnce(first.res).mockResolvedValueOnce(second.res);
  vi.stubGlobal("fetch", fetchFn);
  render(<ContractConversation contractId="c1" initial={[]} />);

  await typeAndAsk(user, "What is the deposit?");
  const [url, init] = fetchFn.mock.calls[0];
  expect(url).toMatch(/\/contracts\/c1\/ask\/stream$/);
  expect(JSON.parse(init.body)).toEqual({ query: "What is the deposit?" });
  expect(init.headers.Authorization).toBe("Bearer tok");

  first.push(stage("scope_check", "Checking your question"));
  expect(await screen.findByText("Checking your question")).toBeInTheDocument();
  first.push(stage("clause_retrieval", "Searching your Contract"));
  expect(await screen.findByText("Searching your Contract")).toBeInTheDocument();
  first.push(frame("answer", ANSWER));
  first.close();
  expect(await screen.findByText("The deposit is Rs. 1,00,000.")).toBeInTheDocument();
  expect(screen.queryByText("Searching your Contract")).not.toBeInTheDocument(); // Stages are done
  expect(screen.getByText("From your Contract and statute text")).toBeInTheDocument();

  // The next Query has Stages of its own.
  await typeAndAsk(user, "And the rent?");
  second.push(stage("scope_check", "Checking your question"));
  expect(await screen.findByText("Checking your question")).toBeInTheDocument();
  second.push(frame("answer", answer({ answer: "Rs. 20,000.", trust_label: "contract", citations: [] })));
  second.close();
  expect(await screen.findByText("Rs. 20,000.")).toBeInTheDocument();
  const asked = screen.getAllByText(/^(What is the deposit\?|And the rent\?)$/).map((e) => e.textContent);
  expect(asked).toEqual(["You asked: What is the deposit?", "You asked: And the rent?"]);
});

it("cancels the Query in flight when a new one is asked", async () => {
  const user = userEvent.setup();
  const slow = controlled();
  const fetchFn = vi
    .fn()
    .mockResolvedValueOnce(slow.res)
    .mockResolvedValueOnce(sseResponse([stage("scope_check", "Checking your question"), frame("answer", answer({ answer: "Rs. 20,000." }))]));
  vi.stubGlobal("fetch", fetchFn);
  render(<ContractConversation contractId="c1" initial={[]} />);

  await typeAndAsk(user, "What is the deposit?");
  slow.push(stage("scope_check", "Checking your question"));
  await screen.findByText("Checking your question");
  expect(fetchFn.mock.calls[0][1].signal.aborted).toBe(false);

  await typeAndAsk(user, "And the rent?");
  expect(fetchFn.mock.calls[0][1].signal.aborted).toBe(true); // the first request was cancelled
  expect(await screen.findByText("Rs. 20,000.")).toBeInTheDocument();
  expect(screen.queryByText("What is the deposit?")).not.toBeInTheDocument(); // and is not shown
  // Whatever the cancelled stream still delivers is ignored.
  slow.push(frame("answer", answer({ answer: "STALE ANSWER" })));
  await waitFor(() => expect(screen.queryByText("STALE ANSWER")).not.toBeInTheDocument());
});

it("explains a failed Query, names the Stage that failed and tries again", async () => {
  const user = userEvent.setup();
  const fetchFn = vi
    .fn()
    .mockResolvedValueOnce(sseResponse([stage("generation", "Writing the answer"), frame("error", { stage: "generation", message: "x" })]))
    .mockResolvedValueOnce(sseResponse([frame("answer", ANSWER)]));
  vi.stubGlobal("fetch", fetchFn);
  render(<ContractConversation contractId="c1" initial={[]} />);

  await typeAndAsk(user, "What is the deposit?");
  expect(await screen.findByRole("alert")).toHaveTextContent(/unavailable/i);
  expect(screen.getByText("Writing the answer")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Try again" }));
  expect(await screen.findByText("The deposit is Rs. 1,00,000.")).toBeInTheDocument();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(JSON.parse(fetchFn.mock.calls[1][1].body)).toEqual({ query: "What is the deposit?" });
});

it("tells the user a rate limit or an unknown Contract plainly", async () => {
  const user = userEvent.setup();
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 404 }));
  render(<ContractConversation contractId="gone" initial={[]} />);
  await typeAndAsk(user, "What is the deposit?");
  expect(await screen.findByRole("alert")).toHaveTextContent(/could not find that contract/i);
});

it("points an unrelated Query to /ask and offers the suggested question", async () => {
  const user = userEvent.setup();
  const refusal = answer({
    response_type: "refusal",
    answer: "That is not about your Contract. For general questions about Indian law, use the Ask page at /ask.",
    refusal_reason: "That is not about your Contract. For general questions about Indian law, use the Ask page at /ask.",
    suggested_reformulation: "What does my Contract say about notice?",
    trust_label: "none",
    citations: [],
    clause_references: [],
    redirect_to_ask: true,
  });
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(sseResponse([frame("answer", refusal)])));
  render(<ContractConversation contractId="c1" initial={[]} />);
  await typeAndAsk(user, "What is the punishment for murder?");
  expect(await screen.findByText(/use the Ask page at \/ask/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /go to the asking screen/i })).toHaveAttribute("href", "/ask");
  await user.click(screen.getByRole("button", { name: "What does my Contract say about notice?" }));
  expect(screen.getByLabelText(/ask a question about this contract/i)).toHaveValue("What does my Contract say about notice?");
});

it("marks a Hindi Query's Stages and answer as Hindi, with the Clause text kept English", async () => {
  const user = userEvent.setup();
  const hindi = answer({ answer: "जमा राशि ₹1,00,000 है।", answer_language: "hi" });
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(sseResponse([stage("scope_check", "आपके प्रश्न की जाँच हो रही है"), frame("answer", hindi)])),
  );
  render(<ContractConversation contractId="c1" initial={[]} />);
  await typeAndAsk(user, "जमा राशि कितनी है?");
  const text = await screen.findByText("जमा राशि ₹1,00,000 है।");
  expect(text.closest("[lang]")).toHaveAttribute("lang", "hi");
  expect(screen.getByText(/The Tenant pays Rs\. 1,00,000\./).closest("[lang]")).toHaveAttribute("lang", "en");
});
