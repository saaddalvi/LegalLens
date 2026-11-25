import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import ContractView from "./contract-view";
import ContractConversation from "./contract-conversation";
import { visit } from "./fake-address";
import { frame } from "./fake-backend";
import type { ContractAnswer, ConversationTurn } from "@/lib/contract-types";

vi.mock("next/navigation", async () => ({
  usePathname: (await import("./fake-address")).usePathname,
  useRouter: () => ({ push: vi.fn() }),
}));

const getToken = vi.fn();
vi.mock("@clerk/nextjs", () => ({ useAuth: () => ({ getToken }) }));

const enc = new TextEncoder();
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

// A "Your Contract, Clause 2" label, whose numbers are links inside it.
const where = (text: string) =>
  screen.getByText((_, el) => el?.tagName === "SPAN" && el.classList.contains("text-sm") && el.textContent === text);

beforeEach(() => {
  getToken.mockResolvedValue("tok");
  visit("/contracts/c1");
});
afterEach(() => {
  vi.unstubAllGlobals();
  getToken.mockReset();
  delete (Element.prototype as Partial<Element>).scrollIntoView; // jsdom has none of its own
});

async function typeAndAsk(user: ReturnType<typeof userEvent.setup>, q: string) {
  await user.type(screen.getByLabelText(/ask a question about this contract/i), q);
  await user.click(screen.getByRole("button", { name: /^Ask/ }));
}

const TURNS: ConversationTurn[] = [
  { query: "What is the deposit?", response: ANSWER },
  { query: "And the notice period?", response: answer({ answer: "Two months.", trust_label: "contract", citations: [], clause_references: [{ number: "7.2", text: "7.2 Notice is two months." }] }) },
];

const listed = (id: string, title: string) => ({
  id,
  title,
  created_at: "2026-03-01T10:00:00Z",
  updated_at: "2026-03-01T10:00:00Z",
});
const DETAIL = {
  id: "c1",
  title: "Rent agreement",
  created_at: "2026-03-01T10:00:00Z",
  page_count: 1,
  clause_count: 1,
  clauses: [{ number: "3", heading: "Deposit", text: "3. Deposit" }],
  brief: null,
  conversations: [listed("newest", "What is the deposit?"), listed("older", "Who repairs?")],
};
const json = (body: unknown) => ({ ok: true, status: 200, json: async () => body });

// A conversation on its own: a new one, or a saved one to be loaded.
function renderConversation({ contractId = "c1", conversationId }: { contractId?: string; conversationId?: string } = {}) {
  render(
    <ContractConversation
      contractId={contractId}
      conversationId={conversationId}
      onSaved={() => {}}
      onMissing={() => {}}
      onGone={() => {}}
      onStartNew={() => {}}
    />,
  );
}

it("shows the most recent conversation in order after a reload, with each answer's sources", async () => {
  const user = userEvent.setup();
  const fetchFn = vi
    .fn()
    .mockResolvedValueOnce(json(DETAIL))
    .mockResolvedValueOnce(json(TURNS))
    .mockResolvedValueOnce(sseResponse([frame("answer", answer({ answer: "Rs. 20,000." }))]));
  vi.stubGlobal("fetch", fetchFn);
  render(<ContractView id="c1" />);
  await screen.findByText("The deposit is Rs. 1,00,000.");
  const queries = screen.getAllByText("You asked:").map((e) => e.parentElement!.textContent);
  expect(queries).toEqual(["You asked: What is the deposit?", "You asked: And the notice period?"]);
  // Answers are shown at once (no reveal), each with its Trust label and Clause reference.
  expect(screen.getByText("The deposit is Rs. 1,00,000.")).toBeInTheDocument();
  expect(screen.getByText("Two months.")).toBeInTheDocument();
  expect([...document.querySelectorAll("[data-trust]")].map((e) => [e.getAttribute("data-trust"), e.textContent])).toEqual([
    ["contract_and_corpus", "From your Contract and statute text"],
    ["contract", "From your Contract"],
  ]);
  // What each rests on is counted, and waits behind the count until asked for.
  expect(screen.queryByRole("link", { name: /Open full Provision/ })).not.toBeInTheDocument();
  expect(where("Your Contract, Clause 3")).not.toBeVisible();
  await user.click(screen.getByRole("button", { name: "Sources: 1 Clause, 1 Citation" }));
  await user.click(screen.getByRole("button", { name: "Sources: 1 Clause" }));
  expect(where("Your Contract, Clause 3")).toBeVisible();
  expect(where("Your Contract, Clause 7.2")).toBeVisible();
  expect(screen.getByRole("link", { name: /Open full Provision: Model Tenancy Act, Section 11/ })).toHaveAttribute(
    "href",
    "/law/Model%20Tenancy%20Act/11",
  );
  const [url, init] = fetchFn.mock.calls[1];
  expect(url).toMatch(/\/contracts\/c1\/conversations\/newest$/);
  expect(init.headers.Authorization).toBe("Bearer tok");
  // The next Query continues the conversation on screen.
  await typeAndAsk(user, "And the rent?");
  expect(await screen.findByText("Rs. 20,000.")).toBeInTheDocument();
  expect(JSON.parse(fetchFn.mock.calls[2][1].body)).toEqual({ query: "And the rent?", conversation_id: "newest" });
});

it("loads no conversation for a Contract that has none", async () => {
  const fetchFn = vi.fn().mockResolvedValue(json({ ...DETAIL, conversations: [] }));
  vi.stubGlobal("fetch", fetchFn);
  render(<ContractView id="c1" />);
  expect(await screen.findByLabelText(/ask a question about this contract/i)).toBeInTheDocument();
  expect(fetchFn).toHaveBeenCalledTimes(1);
});

it("says so when the conversation cannot be loaded, rather than starting another", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValueOnce(json(DETAIL)).mockResolvedValueOnce({ ok: false, status: 503 }),
  );
  render(<ContractView id="c1" />);
  expect(await screen.findByRole("alert")).toHaveTextContent(/unavailable/i);
  expect(screen.queryByLabelText(/ask a question about this contract/i)).not.toBeInTheDocument();
});

it("starts a conversation with the first Query and keeps the later ones in it", async () => {
  const user = userEvent.setup();
  const named = frame("conversation", { id: "new-1", title: "What is the deposit?" });
  const fetchFn = vi
    .fn()
    .mockResolvedValueOnce(sseResponse([frame("error", { stage: "generation", message: "x" })]))
    .mockResolvedValueOnce(sseResponse([named, frame("answer", ANSWER)]))
    .mockResolvedValueOnce(sseResponse([named, frame("answer", answer({ answer: "Rs. 20,000." }))]));
  vi.stubGlobal("fetch", fetchFn);
  renderConversation();
  const sent = (n: number) => JSON.parse(fetchFn.mock.calls[n][1].body);

  await typeAndAsk(user, "What is the deposit?");
  await user.click(await screen.findByRole("button", { name: "Try again" }));
  expect(sent(1)).toEqual({ query: "What is the deposit?" }); // a failed first Query started none
  await screen.findByText("The deposit is Rs. 1,00,000.");
  await typeAndAsk(user, "And the rent?");
  expect(await screen.findByText("Rs. 20,000.")).toBeInTheDocument();
  expect(sent(2)).toEqual({ query: "And the rent?", conversation_id: "new-1" });
});

it("streams the Stages of each Query, then shows its answer", async () => {
  const user = userEvent.setup();
  const first = controlled();
  const second = controlled();
  const fetchFn = vi.fn().mockResolvedValueOnce(first.res).mockResolvedValueOnce(second.res);
  vi.stubGlobal("fetch", fetchFn);
  renderConversation();

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
  renderConversation();

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
  renderConversation();

  await typeAndAsk(user, "What is the deposit?");
  expect(await screen.findByRole("alert")).toHaveTextContent(/unavailable/i);
  expect(screen.getByText("Writing the answer")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Try again" }));
  expect(await screen.findByText("The deposit is Rs. 1,00,000.")).toBeInTheDocument();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(JSON.parse(fetchFn.mock.calls[1][1].body)).toEqual({ query: "What is the deposit?" });
});

it("says a deleted conversation is gone, and Try again starts a new one", async () => {
  const user = userEvent.setup();
  const fetchFn = vi
    .fn()
    .mockResolvedValueOnce(json(TURNS.slice(0, 1)))
    .mockResolvedValueOnce({ ok: false, status: 404 })
    .mockResolvedValueOnce(
      sseResponse([frame("conversation", { id: "new-1", title: "And the rent?" }), frame("answer", answer({ answer: "Rs. 20,000." }))]),
    );
  vi.stubGlobal("fetch", fetchFn);
  renderConversation({ conversationId: "gone" });
  await screen.findByText("The deposit is Rs. 1,00,000.");
  await typeAndAsk(user, "And the rent?");
  expect(await screen.findByRole("alert")).toHaveTextContent(/could not find that conversation/i);
  expect(screen.queryByText("What is the deposit?")).not.toBeInTheDocument(); // its turns went with it
  await user.click(screen.getByRole("button", { name: "Try again" }));
  expect(await screen.findByText("Rs. 20,000.")).toBeInTheDocument();
  expect(JSON.parse(fetchFn.mock.calls[2][1].body)).toEqual({ query: "And the rent?" });
});

it("tells the user a rate limit or an unknown Contract plainly", async () => {
  const user = userEvent.setup();
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 404 }));
  renderConversation({ contractId: "gone" });
  await typeAndAsk(user, "What is the deposit?");
  expect(await screen.findByRole("alert")).toHaveTextContent(/could not find that contract/i);
});

it("carries an unrelated Query to the asking screen and offers the suggested question", async () => {
  const user = userEvent.setup();
  const refusal = answer({
    response_type: "refusal",
    answer: "That is not about your Contract. For general questions about Indian law, use Ask a question.",
    refusal_reason: "That is not about your Contract. For general questions about Indian law, use Ask a question.",
    suggested_reformulation: "What does my Contract say about notice?",
    trust_label: "none",
    citations: [],
    clause_references: [],
    redirect_to_ask: true,
  });
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(sseResponse([frame("answer", refusal)])));
  renderConversation();
  await typeAndAsk(user, "What is the punishment for murder?");
  expect(await screen.findByText(/use Ask a question/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Ask this on the Ask a question page" })).toHaveAttribute(
    "href",
    "/ask?q=What+is+the+punishment+for+murder%3F",
  );
  await user.click(screen.getByRole("button", { name: "What does my Contract say about notice?" }));
  expect(screen.getByLabelText(/ask a question about this contract/i)).toHaveValue("What does my Contract say about notice?");
  expect(screen.getByLabelText(/ask a question about this contract/i)).toHaveFocus(); // ready to send
});

it("marks a Hindi Query's Stages and answer as Hindi, with the Clause text kept English", async () => {
  const user = userEvent.setup();
  const hindi = answer({ answer: "जमा राशि ₹1,00,000 है।", answer_language: "hi" });
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(sseResponse([stage("scope_check", "आपके प्रश्न की जाँच हो रही है"), frame("answer", hindi)])),
  );
  renderConversation();
  await typeAndAsk(user, "जमा राशि कितनी है?");
  const text = await screen.findByText("जमा राशि ₹1,00,000 है।");
  expect(text.closest("[lang]")).toHaveAttribute("lang", "hi");
  expect(screen.getByText(/The Tenant pays Rs\. 1,00,000\./).closest("[lang]")).toHaveAttribute("lang", "en");
});

it("says when the daily limit on questions resets", async () => {
  const user = userEvent.setup();
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: false, status: 429, headers: new Headers({ "Retry-After": "7200", "X-Limit-Scope": "daily" }) }),
  );
  renderConversation();
  await typeAndAsk(user, "What is the deposit?");
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent(/limit of questions about contracts for today/i);
  expect(alert).toHaveTextContent(/2 hours/i);
});

it("keeps the short wait message for the per-minute limit", async () => {
  const user = userEvent.setup();
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: false, status: 429, headers: new Headers({ "Retry-After": "30" }) }),
  );
  renderConversation();
  await typeAndAsk(user, "What is the deposit?");
  expect(await screen.findByRole("alert")).toHaveTextContent(/too many questions/i);
});

it("says when the daily limit resets even when little time is left before midnight", async () => {
  const user = userEvent.setup();
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      headers: new Headers({ "Retry-After": "90", "X-Limit-Scope": "daily" }),
    }),
  );
  renderConversation();
  await typeAndAsk(user, "What is the deposit?");
  expect(await screen.findByRole("alert")).toHaveTextContent(/2 minutes/i);
});

it("puts an answer's headings under the conversation's", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(json(DETAIL)).mockResolvedValueOnce(json(TURNS.slice(0, 1))));
  render(<ContractView id="c1" />);
  await screen.findByText("The deposit is Rs. 1,00,000.");
  await userEvent.click(screen.getByRole("button", { name: /^Sources:/ }));
  const level = (name: string | RegExp) => screen.getByRole("heading", { name }).tagName;
  expect(level("Ask about this Contract")).toBe("H2");
  expect(level("Answer")).toBe("H3");
  expect(level("From your Contract")).toBe("H3");
  expect(level("Citations")).toBe("H3");
  expect(level(/Model Tenancy Act, Section 11/)).toBe("H4");
});

const questionBox = () => screen.getByLabelText(/ask a question about this contract/i);

it("sends on Enter and adds a new line on Shift+Enter", async () => {
  const user = userEvent.setup();
  const fetchFn = vi.fn().mockResolvedValue(sseResponse([frame("answer", ANSWER)]));
  vi.stubGlobal("fetch", fetchFn);
  renderConversation();

  await user.type(questionBox(), "What is the deposit?{Shift>}{Enter}{/Shift}And the rent?");
  expect(questionBox()).toHaveValue("What is the deposit?\nAnd the rent?");
  expect(fetchFn).not.toHaveBeenCalled();
  await user.keyboard("{Enter}");
  expect(await screen.findByText("The deposit is Rs. 1,00,000.")).toBeInTheDocument();
  expect(JSON.parse(fetchFn.mock.calls[0][1].body).query).toBe("What is the deposit?\nAnd the rent?");
  expect(questionBox()).toHaveValue("");
});

it("leaves Enter to an input method that is composing text", async () => {
  const user = userEvent.setup();
  const fetchFn = vi.fn().mockResolvedValue(sseResponse([frame("answer", ANSWER)]));
  vi.stubGlobal("fetch", fetchFn);
  renderConversation();
  await user.type(questionBox(), "जमा राशि");

  // fireEvent returns false when the key's own action was cancelled.
  expect(fireEvent.keyDown(questionBox(), { key: "Enter", isComposing: true })).toBe(true);
  // Safari reports the Enter that ends a composition only by this key code.
  expect(fireEvent.keyDown(questionBox(), { key: "Enter", keyCode: 229 })).toBe(true);
  expect(fetchFn).not.toHaveBeenCalled();
  expect(questionBox()).toHaveValue("जमा राशि");
});

it("sends nothing, and adds no line, for Enter in an empty box", async () => {
  const user = userEvent.setup();
  const fetchFn = vi.fn();
  vi.stubGlobal("fetch", fetchFn);
  renderConversation();
  await user.type(questionBox(), "   {Enter}");
  expect(questionBox()).toHaveValue("   ");
  expect(fetchFn).not.toHaveBeenCalled();
});

it("scrolls each new question to the top of view", async () => {
  const user = userEvent.setup();
  // What was scrolled to, and what it held at that moment.
  const scrolled: { text: string; block?: ScrollLogicalPosition }[] = [];
  Element.prototype.scrollIntoView = function (this: Element, options?: boolean | ScrollIntoViewOptions) {
    scrolled.push({ text: this.textContent!, block: (options as ScrollIntoViewOptions).block });
  };
  vi.stubGlobal(
    "fetch",
    vi.fn()
      .mockResolvedValueOnce(json(TURNS.slice(0, 1)))
      .mockResolvedValueOnce(sseResponse([frame("error", { stage: "generation", message: "x" })]))
      .mockResolvedValueOnce(sseResponse([frame("answer", answer({ answer: "Rs. 20,000." }))])),
  );
  renderConversation({ conversationId: "saved" });
  await screen.findByText("The deposit is Rs. 1,00,000.");
  expect(scrolled).toEqual([]); // a conversation that is only loaded stays where it is

  await user.type(questionBox(), "And the rent?{Enter}");
  expect(scrolled).toEqual([{ text: "You asked: And the rent?", block: "start" }]);
  // Asked again, it is scrolled to again.
  await user.click(await screen.findByRole("button", { name: "Try again" }));
  expect(scrolled).toHaveLength(2);
  expect(scrolled[1].text).toMatch(/^You asked: And the rent\?/);
  expect(await screen.findByText("Rs. 20,000.")).toBeInTheDocument();
  expect(scrolled).toHaveLength(2); // the answer arriving does not move the reader
});

const flagged = (number: string) => ({
  clause_reference: { number, text: `${number}.` },
  how_it_differs: "It differs.",
  citations: [],
});

// A Contract's page on an empty conversation, whose brief flags these Clauses in this order.
async function openEmpty(flaggedNumbers: string[] | null) {
  const fetchFn = vi
    .fn()
    .mockResolvedValueOnce(
      json({
        ...DETAIL,
        clauses: [
          { number: "0", heading: "", text: "RENT AGREEMENT" },
          { number: "3", heading: "", text: "3. The Tenant pays the deposit." },
          { number: "5", heading: "Notice", text: "5. Notice\nEither side gives two months." },
          { number: "7", heading: "The Tenant shall pay the rent to", text: "7. The Tenant shall pay the rent to\nthe Landlord." },
          { number: "9", heading: "Security deposit", text: "9. Security deposit\nOne lakh is held." },
        ],
        brief: flaggedNumbers && {
          parties: [],
          purpose: "A lease.",
          key_terms: [],
          obligations: [],
          flagged_clauses: flaggedNumbers.map(flagged),
        },
        conversations: [],
      }),
    )
    .mockResolvedValue(sseResponse([frame("answer", ANSWER)]));
  vi.stubGlobal("fetch", fetchFn);
  render(<ContractView id="c1" />);
  const list = await screen.findByRole("list", { name: "Questions to start with" });
  return {
    fetchFn,
    starters: () => within(list).getAllByRole("button").map((b) => b.textContent),
  };
}

const about = (subject: string) => `What does ${subject} say, and what does Indian law provide?`;
const GENERIC = [
  "What must I do under this Contract?",
  "How can this Contract be ended?",
  "What happens if either side breaks this Contract?",
];

it("starts an empty conversation with questions about the first three Flagged clauses", async () => {
  const user = userEvent.setup();
  // Clause 9 is flagged twice, and asked about once.
  const { fetchFn, starters } = await openEmpty(["9", "9", "3", "5", "7"]);
  expect(starters()).toEqual([
    about("Clause 9 (Security deposit)"),
    about("Clause 3"),
    about("Clause 5 (Notice)"),
  ]);
  expect(fetchFn).toHaveBeenCalledTimes(1); // nothing was asked of a model to build them

  await user.click(screen.getByRole("button", { name: about("Clause 9 (Security deposit)") }));
  expect(await screen.findByText("The deposit is Rs. 1,00,000.")).toBeInTheDocument();
  expect(JSON.parse(fetchFn.mock.calls[1][1].body)).toEqual({ query: about("Clause 9 (Security deposit)") });
  expect(screen.getByText("You asked:").parentElement).toHaveTextContent(about("Clause 9 (Security deposit)"));
  expect(screen.queryByRole("list", { name: "Questions to start with" })).not.toBeInTheDocument();
});

it("leaves out a heading that is the start of a sentence, and calls Clause 0 the Recitals", async () => {
  const { starters } = await openEmpty(["7", "0"]);
  expect(starters()).toEqual([about("Clause 7"), "What do the Recitals say, and what does Indian law provide?", GENERIC[0]]);
});

it("fills the places a single Flagged clause leaves with general questions", async () => {
  const { starters } = await openEmpty(["3"]);
  expect(starters()).toEqual([about("Clause 3"), GENERIC[0], GENERIC[1]]);
});

it.each([
  ["no Flagged clauses", []],
  ["no brief", null],
])("starts a Contract with %s on general questions", async (_, numbers) => {
  const { starters } = await openEmpty(numbers);
  expect(starters()).toEqual(GENERIC);
});

it("moves focus to the question just asked, and on to the box when it is answered", async () => {
  const user = userEvent.setup();
  const stream = controlled();
  vi.stubGlobal(
    "fetch",
    vi.fn()
      .mockResolvedValueOnce(sseResponse([frame("error", { stage: "generation", message: "x" })]))
      .mockResolvedValueOnce(stream.res),
  );
  renderConversation();
  await typeAndAsk(user, "What is the deposit?");
  // The button pressed goes away with the error, so focus is put on the question asked again.
  await user.click(await screen.findByRole("button", { name: "Try again" }));
  const question = screen.getByText("You asked:").parentElement!;
  expect(question).toHaveFocus();
  expect(screen.getByRole("status", { name: "Answer notice" })).toBeEmptyDOMElement();

  stream.push(frame("answer", ANSWER));
  expect(await screen.findByText("The deposit is Rs. 1,00,000.")).toBeInTheDocument();
  expect(questionBox()).toHaveFocus();
  expect(screen.getByRole("status", { name: "Answer notice" })).toHaveTextContent("Your answer is ready.");
});

it("leaves focus where the reader has moved it while the answer was written", async () => {
  const user = userEvent.setup();
  const stream = controlled();
  vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(json(TURNS.slice(0, 1))).mockResolvedValueOnce(stream.res));
  renderConversation({ conversationId: "saved" });
  await screen.findByText("The deposit is Rs. 1,00,000.");
  await user.type(questionBox(), "And the rent?{Enter}");
  const elsewhere = screen.getByRole("button", { name: /^Sources:/ });
  elsewhere.focus();
  stream.push(frame("answer", answer({ answer: "Rs. 20,000.", citations: [], clause_references: [] })));
  expect(await screen.findByText("Rs. 20,000.")).toBeInTheDocument();
  expect(elsewhere).toHaveFocus();
});

it("keeps focus on the question when its conversation turns out to be gone", async () => {
  const user = userEvent.setup();
  vi.stubGlobal(
    "fetch",
    vi.fn()
      .mockResolvedValueOnce(json(TURNS.slice(0, 1)))
      .mockResolvedValueOnce({ ok: false, status: 503 })
      .mockResolvedValueOnce({ ok: false, status: 404 }),
  );
  renderConversation({ conversationId: "gone" });
  await screen.findByText("The deposit is Rs. 1,00,000.");
  await typeAndAsk(user, "And the rent?");
  await user.click(await screen.findByRole("button", { name: "Try again" }));
  expect(await screen.findByText(/could not find that conversation/i)).toBeInTheDocument();
  expect(screen.getByText("You asked:").parentElement).toHaveFocus();
});

it("opens the folded sources on the Citation a mention in the answer names", async () => {
  const user = userEvent.setup();
  Element.prototype.scrollIntoView = vi.fn();
  const mentions = answer({ answer: "Section 11 of the Model Tenancy Act caps the deposit." });
  vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(json([{ query: "What is the cap?", response: mentions }])));
  renderConversation({ conversationId: "saved" });
  const toggle = await screen.findByRole("button", { name: /^Sources:/ });
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  await user.click(screen.getByRole("button", { name: /^Section 11/ }));
  expect(toggle).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByText(/security deposit shall not exceed two months/)).toBeVisible();
});

it("says a Citation is repealed while the sources are still folded", async () => {
  const repealed = answer({ citations: [{ ...ANSWER.citations[0], status: "repealed" }] });
  vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(json([{ query: "What is the cap?", response: repealed }])));
  renderConversation({ conversationId: "saved" });
  expect(await screen.findByRole("button", { name: /^Sources: 1 Clause, 1 Citation\s*\(1 repealed\)$/ })).toBeVisible();
});
