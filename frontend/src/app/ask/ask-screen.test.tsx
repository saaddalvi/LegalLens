import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Activity } from "react";
import AskScreen from "./ask-screen";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

const getToken = vi.fn();
const session: { isLoaded?: boolean; isSignedIn?: boolean; userId?: string | null } = {};
vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ getToken, isLoaded: true, userId: "user_1", ...session }),
  SignInButton: ({ children }: { children: React.ReactNode }) => children,
  UserButton: () => null,
}));

const base = {
  response_type: "answer",
  refusal_reason: null,
  suggested_reformulation: null,
  answer: "Equality before the law is guaranteed.",
  answer_language: "en",
  trust_label: "corpus",
  citations: [
    {
      act: "Constitution of India",
      chapter: "Part III",
      number: "14",
      status: "in_force",
      text: "The State shall not deny to any person equality before the law.",
      superseded_by: null,
      supersedes: null,
    },
  ],
  fallback_sources: [],
};

const enc = new TextEncoder();
const frame = (name: string, data: unknown) => `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`;
const stageFrame = (id: string, label: string) => frame("stage", { id, label });

// A Response whose body streams the given SSE text, one chunk at a time.
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
function controlledResponse() {
  let ctrl!: ReadableStreamDefaultController<Uint8Array>;
  const body = new ReadableStream<Uint8Array>({ start: (c) => (ctrl = c) });
  return {
    res: { ok: true, status: 200, body },
    push: (t: string) => ctrl.enqueue(enc.encode(t)),
    close: () => ctrl.close(),
  };
}

function mockFetch(res: { ok: boolean; status: number; body?: unknown }) {
  const fn = vi.fn().mockImplementation(async () =>
    res.ok
      ? sseResponse([stageFrame("scope_check", "Checking your question"), frame("answer", res.body)])
      : { ok: false, status: res.status },
  );
  vi.stubGlobal("fetch", fn);
  return fn;
}

const question = () => screen.getByRole("heading", { level: 1 });

// Unfolds the form to the question asked and sends it again.
async function askAgain() {
  await userEvent.click(screen.getByRole("button", { name: "Edit question" }));
  await userEvent.click(screen.getByRole("button", { name: "Ask" }));
}

async function ask() {
  const user = userEvent.setup();
  render(<AskScreen />);
  await user.type(screen.getByLabelText(/ask a question/i), "What is Article 14?");
  await user.click(screen.getByRole("button", { name: "Ask" }));
  return user;
}

beforeEach(() => getToken.mockResolvedValue("session-token"));

afterEach(() => {
  vi.unstubAllGlobals();
  push.mockReset();
  getToken.mockReset();
  delete session.isLoaded;
  delete session.isSignedIn;
  delete session.userId;
  window.sessionStorage.clear();
});

describe("AskScreen", () => {
  it("shows the disclaimer, Trust label and Citations", async () => {
    mockFetch({ ok: true, status: 200, body: base });
    await ask();
    expect(screen.getByText(/not legal advice/i)).toBeInTheDocument();
    expect(await screen.findByText("From statute text")).toBeInTheDocument();
    expect(screen.getByText(/Constitution of India, Article 14/)).toBeInTheDocument();
  });

  it("keeps one disclaimer, beside the answer once there is one", async () => {
    mockFetch({ ok: true, status: 200, body: base });
    await ask();
    await screen.findByRole("button", { name: "Copy answer" });
    expect(screen.getByRole("region", { name: "Answer" })).toHaveTextContent(/not legal advice/i);
    expect(screen.getAllByText(/not legal advice/i)).toHaveLength(1);
  });

  it("says under the question box that Hindi is accepted", () => {
    render(<AskScreen />);
    expect(screen.getByText("आप हिंदी में भी पूछ सकते हैं।")).toHaveAttribute("lang", "hi");
  });

  it("expands and collapses a Citation", async () => {
    mockFetch({ ok: true, status: 200, body: base });
    const user = await ask();
    const toggle = await screen.findByRole("button", { name: /Constitution of India, Article 14/ });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText(/shall not deny to any person/)).toBeVisible();
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText(/shall not deny to any person/)).not.toBeInTheDocument();
  });

  it("shows a model Act Citation as not in force by itself", async () => {
    mockFetch({
      ok: true,
      status: 200,
      body: {
        ...base,
        citations: [
          {
            ...base.citations[0],
            act: "Model Tenancy Act",
            chapter: "Security deposit",
            number: "11",
            status: "model",
            text: "The security deposit shall not exceed two months' rent.",
          },
        ],
      },
    });
    const user = await ask();
    const toggle = await screen.findByRole("button", { name: /Model Tenancy Act, Section 11/ });
    expect(toggle).toHaveTextContent(/model Act, not in force by itself/);
    expect(toggle).not.toHaveTextContent(/\bin force\)/);
    await user.click(toggle);
    const note = screen
      .getAllByRole("note")
      .find((n) => /model Act, a template/.test(n.textContent ?? ""));
    expect(note).toHaveTextContent(/State's own law may differ/);
  });

  it("labels Fallback answers as lower trust and lists sources", async () => {
    mockFetch({
      ok: true,
      status: 200,
      body: {
        ...base,
        trust_label: "fallback",
        citations: [],
        fallback_sources: [{ title: "Example Law Blog", url: "https://example.com/a", snippet: "s" }],
      },
    });
    await ask();
    expect(await screen.findByText(/less reliable/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Example Law Blog" })).toHaveAttribute(
      "href",
      "https://example.com/a",
    );
  });

  it("shows a loading state while waiting", async () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
    await ask();
    // The form folds to the question, which takes the focus.
    expect(question()).toHaveTextContent("What is Article 14?");
    expect(question()).toHaveFocus();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    // Unfolded, it cannot send a second request while the first is running.
    await userEvent.click(screen.getByRole("button", { name: "Edit question" }));
    const button = screen.getByRole("button", { name: /thinking/i });
    expect(button).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(button);
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("status", { name: /progress/i })).toBeInTheDocument();
  });

  it("explains rate limits", async () => {
    mockFetch({ ok: false, status: 429 });
    await ask();
    expect(await screen.findByRole("alert")).toHaveTextContent(/too many questions/i);
  });

  it("says how long to wait when the limit will not lift for hours", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 429,
        headers: new Headers({ "Retry-After": "19800" }),
      }),
    );
    await ask();
    expect(await screen.findByRole("alert")).toHaveTextContent("try again in 5 hours 30 minutes");
  });

  it("offers sign-in instead of Try again once the session has ended", async () => {
    session.isSignedIn = false;
    mockFetch({ ok: false, status: 401 });
    render(<AskScreen initialQuery="What is Article 14?" />);
    const alert = await screen.findByRole("alert");
    expect(within(alert).getByRole("button", { name: "Sign in" })).toBeInTheDocument();
    expect(within(alert).queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
  });

  it("asks for a question when the box is empty", async () => {
    const fn = mockFetch({ ok: true, status: 200, body: base });
    const user = userEvent.setup();
    render(<AskScreen />);
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(screen.getByText("Type your question first, in English or Hindi.")).toBeInTheDocument();
    expect(screen.getByLabelText(/ask a question/i)).toBeInvalid();
    expect(fn).not.toHaveBeenCalled();
  });

  it("stops at the longest Query and counts down near it", () => {
    render(<AskScreen />);
    const box = screen.getByLabelText(/ask a question/i);
    expect(box).toHaveAttribute("maxlength", "2000");
    expect(screen.queryByText(/characters left/)).not.toBeInTheDocument();
    fireEvent.change(box, { target: { value: "a".repeat(1900) } });
    expect(screen.getByText("100 characters left")).toBeInTheDocument();
  });

  it("announces that the answer is ready", async () => {
    mockFetch({ ok: true, status: 200, body: base });
    await ask();
    expect(await screen.findByText("Your answer is ready.")).toHaveAttribute("role", "status");
  });

  const refused = {
    ...base,
    response_type: "refusal",
    refusal_reason: "LegalLens cannot choose for you.",
    suggested_reformulation: "What does Article 14 say?",
    answer: "",
    citations: [],
  };

  it("asks a suggested question in one press", async () => {
    const fn = mockFetch({ ok: true, status: 200, body: refused });
    const user = await ask();
    const suggested = await screen.findByRole("button", { name: "Ask this instead" });
    expect(suggested).toHaveAccessibleDescription("What does Article 14 say?");
    mockFetch({ ok: true, status: 200, body: base });
    const next = vi.mocked(globalThis.fetch);
    await user.click(suggested);
    expect(await screen.findByText("From statute text")).toBeInTheDocument();
    expect(fn).toHaveBeenCalledTimes(1);
    expect(next).toHaveBeenCalledTimes(1);
    expect(JSON.parse(next.mock.calls[0][1]!.body as string)).toEqual({ query: "What does Article 14 say?" });
    expect(question()).toHaveTextContent("What does Article 14 say?");
    expect(question()).toHaveFocus();
    expect(push).toHaveBeenLastCalledWith("/ask?q=What+does+Article+14+say%3F", expect.anything());
  });

  it("marks the language of a suggested question", async () => {
    mockFetch({
      ok: true,
      status: 200,
      body: { ...refused, answer_language: "hi", suggested_reformulation: "अनुच्छेद 14 क्या कहता है?" },
    });
    await ask();
    expect(await screen.findByText("अनुच्छेद 14 क्या कहता है?")).toHaveAttribute("lang", "hi");
  });

  it("offers nothing to ask when a refusal suggests nothing", async () => {
    mockFetch({ ok: true, status: 200, body: { ...refused, suggested_reformulation: null } });
    await ask();
    await screen.findByRole("status", { name: "Refusal" });
    expect(screen.queryByRole("button", { name: "Ask this instead" })).not.toBeInTheDocument();
  });

  it("opens a mentioned Provision from the keyboard", async () => {
    mockFetch({ ok: true, status: 200, body: { ...base, answer: "See Article 14." } });
    const user = await ask();
    (await screen.findByRole("button", { name: "Article 14" })).focus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("button", { name: /Constitution of India, Article 14/ })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
  });

  it("sends the Clerk session token as a bearer token", async () => {
    const fn = mockFetch({ ok: true, status: 200, body: base });
    await ask();
    await screen.findByText("From statute text");
    expect(fn.mock.calls[0][1].headers).toMatchObject({
      Authorization: "Bearer session-token",
    });
  });

  it("asks the reader to sign in again when the service answers 401", async () => {
    mockFetch({ ok: false, status: 401 });
    await ask();
    expect(await screen.findByRole("alert")).toHaveTextContent(/sign in again/i);
  });

  it("explains service errors", async () => {
    mockFetch({ ok: false, status: 503 });
    await ask();
    expect(await screen.findByRole("alert")).toHaveTextContent(/unavailable/i);
  });

  it("explains network failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fail")));
    await ask();
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/could not reach/i),
    );
  });

  it("submits the initial Query at once and fills the ask box", async () => {
    const fn = mockFetch({ ok: true, status: 200, body: base });
    render(<AskScreen initialQuery="What is Article 14?" />);
    expect(await screen.findByText("From statute text")).toBeInTheDocument();
    expect(fn).toHaveBeenCalledTimes(1);
    expect(JSON.parse(fn.mock.calls[0][1].body)).toEqual({ query: "What is Article 14?" });
    expect(question()).toHaveTextContent("What is Article 14?");
    expect(push).not.toHaveBeenCalled();
  });

  it("submits nothing without an initial Query", () => {
    const fn = mockFetch({ ok: true, status: 200, body: base });
    render(<AskScreen />);
    expect(fn).not.toHaveBeenCalled();
  });

  it("puts a submitted Query in the address as a new history entry", async () => {
    mockFetch({ ok: true, status: 200, body: base });
    await ask();
    expect(push).toHaveBeenCalledWith("/ask?q=What+is+Article+14%3F", expect.anything());
  });

  it("shows the earlier Query's answer again when the address goes back to it", async () => {
    const answer = (text: string) => ({ ...base, answer: text });
    const fn = vi
      .fn()
      .mockResolvedValueOnce(sseResponse([frame("answer", answer("First answer."))]))
      .mockResolvedValueOnce(sseResponse([frame("answer", answer("Second answer."))]));
    vi.stubGlobal("fetch", fn);
    const { rerender } = render(<AskScreen initialQuery="first" />);
    expect(await screen.findByText("First answer.")).toBeInTheDocument();
    rerender(<AskScreen initialQuery="second" />);
    expect(await screen.findByText("Second answer.")).toBeInTheDocument();
    expect(question()).toHaveTextContent("second");
    rerender(<AskScreen initialQuery="first" />);
    expect(screen.getByText("First answer.")).toBeInTheDocument();
    expect(screen.queryByText("Second answer.")).not.toBeInTheDocument();
    expect(question()).toHaveTextContent("first");
    expect(screen.queryByRole("status", { name: /progress/i })).not.toBeInTheDocument();
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it("does not submit twice when the address catches up with a typed Query", async () => {
    const fn = mockFetch({ ok: true, status: 200, body: base });
    const user = userEvent.setup();
    const { rerender } = render(<AskScreen />);
    await user.type(screen.getByLabelText(/ask a question/i), "What is Article 14?");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    await screen.findByText("From statute text");
    rerender(<AskScreen initialQuery="What is Article 14?" />);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("clears the screen when the address goes back to /ask without a Query", async () => {
    mockFetch({ ok: true, status: 200, body: base });
    const { rerender } = render(<AskScreen initialQuery="What is Article 14?" />);
    await screen.findByText("From statute text");
    rerender(<AskScreen />);
    expect(screen.queryByText("From statute text")).not.toBeInTheDocument();
    expect(screen.getByLabelText(/ask a question/i)).toHaveValue("");
  });

  it("posts to the stream endpoint and shows Stages in order with the active one marked", async () => {
    const live = controlledResponse();
    const fn = vi.fn().mockResolvedValue(live.res);
    vi.stubGlobal("fetch", fn);
    await ask();
    expect(fn.mock.calls[0][0]).toMatch(/\/ask\/stream$/);
    live.push(stageFrame("scope_check", "Checking your question"));
    live.push(stageFrame("retrieval", "Searching the statutes"));
    await waitFor(() => expect(screen.getAllByRole("listitem")).toHaveLength(2));
    const [first, second] = screen.getAllByRole("listitem");
    expect(first).toHaveTextContent("Checking your question (done)");
    expect(second).toHaveTextContent("Searching the statutes (in progress)");
    live.push(frame("answer", base));
    live.close();
    expect(await screen.findByText("From statute text")).toBeInTheDocument();
    expect(screen.queryByRole("listitem")).not.toBeInTheDocument();
    expect(screen.getByText(/not legal advice/i)).toBeInTheDocument();
  });

  it("handles frames split across chunks", async () => {
    const text = stageFrame("scope_check", "Checking your question") + frame("answer", base);
    const mid = Math.floor(text.length / 2);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(sseResponse([text.slice(0, mid), text.slice(mid)])));
    await ask();
    expect(await screen.findByText("From statute text")).toBeInTheDocument();
  });

  it("skips a malformed frame, ignores keepalives and keeps a final frame with no blank line", async () => {
    const text =
      ": keepalive\n\n" +
      "event: stage\ndata: {oops\n\n" +
      stageFrame("scope_check", "Checking your question") +
      frame("answer", base).trimEnd();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(sseResponse([text])));
    await ask();
    expect(await screen.findByText("From statute text")).toBeInTheDocument();
  });

  it("shows a starting message before the first Stage arrives", async () => {
    const live = controlledResponse();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(live.res));
    await ask();
    expect(await screen.findByText("Starting…")).toBeInTheDocument();
    live.close();
  });

  it("shows the existing message when the stream reports an error or drops", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(sseResponse([frame("error", { stage: "grading", message: "x" })])),
    );
    await ask();
    expect(await screen.findByRole("alert")).toHaveTextContent(/unavailable/i);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(sseResponse([stageFrame("scope_check", "Checking")])));
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Edit question" }));
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/could not reach/i);
  });

  it("marks the running Stage failed after an error event and Try again resubmits the Query", async () => {
    const fn = vi
      .fn()
      .mockResolvedValueOnce(
        sseResponse([
          stageFrame("scope_check", "Checking your question"),
          stageFrame("generation", "Writing the answer"),
          frame("error", { stage: "generation", message: "x" }),
        ]),
      )
      .mockResolvedValueOnce(sseResponse([frame("answer", base)]));
    vi.stubGlobal("fetch", fn);
    const user = await ask();
    expect(await screen.findByRole("alert")).toHaveTextContent(/unavailable/i);
    const failed = screen.getByText("Writing the answer").closest("li")!;
    expect(failed).toHaveTextContent(/failed/i);
    expect(screen.getByText("Checking your question").closest("li")).toHaveTextContent(/done/i);
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText(/Equality before the law/)).toBeInTheDocument();
    expect(fn).toHaveBeenCalledTimes(2);
    expect(JSON.parse(fn.mock.calls[1][1].body)).toEqual({ query: "What is Article 14?" });
    expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
  });

  it("treats a stream that ends without an answer or error as a failure of the running Stage", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        sseResponse([stageFrame("scope_check", "Checking"), stageFrame("retrieval", "Searching")]),
      ),
    );
    await ask();
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Searching").closest("li")).toHaveTextContent(/failed/i);
    expect(screen.getByRole("button", { name: "Try again" })).toBeEnabled();
  });

  it("shows only the new Query's Stages and answer when another Query replaces one in flight", async () => {
    const first = controlledResponse();
    const fn = vi
      .fn()
      .mockResolvedValueOnce(first.res)
      .mockResolvedValueOnce(
        sseResponse([
          stageFrame("scope_check", "Second stage"),
          frame("answer", { ...base, answer: "Second answer." }),
        ]),
      );
    vi.stubGlobal("fetch", fn);
    const { rerender } = render(<AskScreen initialQuery="first" />);
    first.push(stageFrame("scope_check", "First stage"));
    await screen.findByText("First stage");
    rerender(<AskScreen initialQuery="second" />);
    expect(await screen.findByText("Second answer.")).toBeInTheDocument();
    first.push(frame("answer", { ...base, answer: "First answer." }));
    await Promise.resolve();
    expect(screen.queryByText("First stage")).not.toBeInTheDocument();
    expect(screen.queryByText("First answer.")).not.toBeInTheDocument();
  });
});

describe("answer reveal", () => {
  const longAnswer = Array.from({ length: 200 }, (_, i) => `word${i}`).join(" ");
  const hindiAnswer = "अनुच्छेद 14 के अनुसार कानून के समक्ष सभी व्यक्ति समान हैं।\n\nयह अधिकार सभी को मिलता है।";

  function allowMotion() {
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: false,
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
    }));
  }

  async function startAnswering(body: object) {
    allowMotion();
    vi.useFakeTimers();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(sseResponse([frame("answer", body)])));
    render(<AskScreen initialQuery="What is Article 14?" />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
  }

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows the Trust label at once, then the Citations when the reveal ends", async () => {
    await startAnswering({ ...base, answer: longAnswer });
    const section = screen.getByRole("region", { name: "Answer" });
    expect(section).toHaveTextContent(longAnswer);
    expect(screen.getByText("From statute text")).toBeInTheDocument();
    expect(screen.queryByText(/Constitution of India/)).not.toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(screen.queryByText(/Constitution of India/)).not.toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(400);
    });
    expect(screen.getByText(/Constitution of India/)).toBeInTheDocument();
  });

  it("shows the Citations at once when the answer is clicked", async () => {
    await startAnswering({ ...base, answer: longAnswer });
    expect(screen.queryByText(/Constitution of India/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByText(/word0/));
    expect(screen.getByText("From statute text")).toBeInTheDocument();
    expect(screen.getByText(/Constitution of India/)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Answer" })).toHaveTextContent(longAnswer);
  });

  it("shows the Citations at once when Escape is pressed", async () => {
    await startAnswering({ ...base, answer: longAnswer });
    expect(screen.queryByText(/Constitution of India/)).not.toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.getByText(/Constitution of India/)).toBeInTheDocument();
  });

  it("does not reveal an answer afresh when the screen is shown again", async () => {
    allowMotion();
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(sseResponse([frame("answer", { ...base, answer: longAnswer })])),
    );
    const view = (mode: "visible" | "hidden") => (
      <Activity mode={mode}>
        <AskScreen initialQuery="What is Article 14?" />
      </Activity>
    );
    const { rerender, container } = render(view("visible"));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(container.querySelector(".reveal-word")).not.toBeNull();
    await act(async () => rerender(view("hidden")));
    await act(async () => rerender(view("visible")));
    expect(container.querySelector(".reveal-word, .reveal-in")).toBeNull();
    expect(screen.getByText(/Constitution of India/)).toBeInTheDocument();
  });

  it("says what a web-sourced Trust label means before the answer, and nothing extra for statute text", async () => {
    await startAnswering({ ...base, answer: "Short.", trust_label: "fallback" });
    expect(screen.getByText(/draws on web search/)).toBeInTheDocument();
    cleanup();
    window.sessionStorage.clear();
    await startAnswering({ ...base, answer: "Short." });
    expect(screen.queryByText(/Every claim rests on/)).not.toBeInTheDocument();
  });

  it("reveals a refusal the same way", async () => {
    await startAnswering({
      ...base,
      response_type: "refusal",
      refusal_reason: "This is outside Indian law.",
      suggested_reformulation: "What does Article 14 say?",
      answer: "",
      citations: [],
    });
    const refusal = screen.getByRole("status", { name: "Refusal" });
    expect(refusal).toHaveTextContent("This is outside Indian law.");
    expect(screen.queryByRole("button", { name: "Ask this instead" })).not.toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(900);
    });
    expect(screen.getByRole("button", { name: "Ask this instead" })).toBeInTheDocument();
  });

  it("keeps Hindi words whole and the complete text readable during the reveal", async () => {
    await startAnswering({ ...base, answer: hindiAnswer, answer_language: "hi" });
    const section = screen.getByRole("region", { name: "Answer" });
    expect(section.textContent).toContain("अनुच्छेद 14 के अनुसार कानून के समक्ष सभी व्यक्ति समान हैं।");
    expect(section.textContent).toContain("यह अधिकार सभी को मिलता है।");
    expect(section.querySelector("[aria-hidden='true']")).toBeNull();
    expect(section.querySelector("[aria-live]")).toBeNull();
  });
});

describe("Provision mentions in answers", () => {
  const bns = {
    ...base.citations[0],
    act: "Bharatiya Nyaya Sanhita",
    chapter: "Offences affecting the human body",
    number: "103",
    text: "Whoever commits murder shall be punished with death or imprisonment for life.",
  };
  const withAnswer = (answer: string, extra: Partial<typeof base> = {}) =>
    mockFetch({
      ok: true,
      status: 200,
      body: { ...base, answer, citations: [base.citations[0], bns], ...extra },
    });

  it("turns a mention of a cited Provision into a chip that opens its Citation card", async () => {
    withAnswer("Murder is punished under BNS 103. Equality is in Article 14.");
    const user = await ask();
    const chip = await screen.findByRole("button", { name: "BNS 103" });
    const toggle = screen.getByRole("button", { name: /Bharatiya Nyaya Sanhita, Section 103/ });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await user.click(chip);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText(/commits murder/)).toBeVisible();
    // Clicking again keeps the card open rather than toggling it shut.
    await user.click(chip);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
  });

  it("matches 'Article 14' and 'section 103 of the Bharatiya Nyaya Sanhita'", async () => {
    withAnswer("See Article 14 and section 103 of the Bharatiya Nyaya Sanhita.");
    await ask();
    expect(await screen.findByRole("button", { name: "Article 14" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "section 103 of the Bharatiya Nyaya Sanhita" }),
    ).toBeInTheDocument();
  });

  it("matches mentions in Hindi answer text", async () => {
    withAnswer("हत्या की सज़ा BNS 103 में है। देखें अनुच्छेद 14 और धारा 103 BNS।", {
      answer_language: "hi",
    });
    await ask();
    expect(await screen.findAllByRole("button", { name: /BNS 103|धारा 103 BNS/ })).toHaveLength(2);
    expect(screen.getByRole("button", { name: "अनुच्छेद 14" })).toBeInTheDocument();
  });

  it("does not link a Provision that was not cited", async () => {
    withAnswer("Murder was IPC 302 and theft is BNS 303.");
    await ask();
    await screen.findByText("From statute text");
    expect(screen.queryByRole("button", { name: /IPC 302|BNS 303/ })).not.toBeInTheDocument();
    expect(screen.getByText(/Murder was IPC 302 and theft is BNS 303\./)).toBeInTheDocument();
  });

  it("keeps the answer text whole around chips", async () => {
    withAnswer("Murder is punished under BNS 103, which is serious.");
    await ask();
    await screen.findByRole("button", { name: "BNS 103" });
    expect(screen.getByLabelText("Answer").textContent).toContain(
      "Murder is punished under BNS 103, which is serious.",
    );
  });
});

describe("chip case handling", () => {
  it("opens and focuses the card when the answer's number differs in case", async () => {
    mockFetch({
      ok: true,
      status: 200,
      body: {
        ...base,
        answer: "See BNS 103a.",
        citations: [{ ...base.citations[0], act: "Bharatiya Nyaya Sanhita", number: "103A" }],
      },
    });
    const user = await ask();
    await user.click(await screen.findByRole("button", { name: "BNS 103a" }));
    const toggle = screen.getByRole("button", { name: /Bharatiya Nyaya Sanhita, Section 103A/ });
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(toggle).toHaveFocus();
  });
});

describe("Copy answer", () => {
  function stubClipboard(writeText: (text: string) => Promise<void>) {
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
  }

  it("copies the answer, its Citations and the disclaimer, and says so", async () => {
    mockFetch({ ok: true, status: 200, body: base });
    await ask();
    const writeText = vi.fn().mockResolvedValue(undefined);
    stubClipboard(writeText);
    fireEvent.click(await screen.findByRole("button", { name: "Copy answer" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1));
    const copied = writeText.mock.calls[0][0] as string;
    expect(copied).toContain("Equality before the law is guaranteed.");
    expect(copied).toContain("- Constitution of India, Article 14");
    expect(copied.startsWith("Question: What is Article 14?\n\nFrom statute text")).toBe(true);
    expect(copied).toContain(`${window.location.origin}/law/Constitution%20of%20India/14`);
    expect(copied).toMatch(/not legal advice/i);
    expect(await screen.findByText("Copied")).toBeInTheDocument();
  });

  it("says when the answer could not be copied", async () => {
    mockFetch({ ok: true, status: 200, body: base });
    await ask();
    stubClipboard(vi.fn().mockRejectedValue(new Error("denied")));
    fireEvent.click(await screen.findByRole("button", { name: "Copy answer" }));
    expect(await screen.findByText("Could not copy")).toBeInTheDocument();
  });

  it("says so when the browser has no clipboard", async () => {
    mockFetch({ ok: true, status: 200, body: base });
    await ask();
    Object.defineProperty(navigator, "clipboard", { value: undefined, configurable: true });
    fireEvent.click(await screen.findByRole("button", { name: "Copy answer" }));
    expect(await screen.findByText("Could not copy")).toBeInTheDocument();
  });

  it("is not offered on a refusal", async () => {
    mockFetch({
      ok: true,
      status: 200,
      body: {
        ...base,
        response_type: "refusal",
        refusal_reason: "This is outside Indian law.",
        answer: "",
        citations: [],
      },
    });
    await ask();
    await screen.findByRole("status", { name: "Refusal" });
    expect(screen.queryByRole("button", { name: "Copy answer" })).not.toBeInTheDocument();
  });
});

describe("Citation links to the law", () => {
  it("links each Citation card to the full Provision", async () => {
    mockFetch({ ok: true, status: 200, body: base });
    await ask();
    const link = await screen.findByRole("link", { name: /Open full Provision: Constitution of India, Article 14/ });
    expect(link).toHaveAttribute("href", "/law/Constitution%20of%20India/14");
  });

  it("links a repealed Citation to the law that replaced it, and a replacing one to its predecessor", async () => {
    mockFetch({
      ok: true,
      status: 200,
      body: {
        ...base,
        citations: [
          {
            ...base.citations[0],
            act: "Indian Penal Code",
            number: "302",
            status: "repealed",
            superseded_by: "Bharatiya Nyaya Sanhita 103",
          },
          {
            ...base.citations[0],
            act: "Bharatiya Nyaya Sanhita",
            number: "103",
            supersedes: "Indian Penal Code 302",
          },
        ],
      },
    });
    const user = await ask();
    const note = (await screen.findAllByRole("note")).find((n) => /has been repealed/.test(n.textContent ?? ""))!;
    expect(note).toHaveTextContent("The current law is Bharatiya Nyaya Sanhita, Section 103.");
    expect(within(note).getByRole("link", { name: "Bharatiya Nyaya Sanhita, Section 103" })).toHaveAttribute(
      "href",
      "/law/Bharatiya%20Nyaya%20Sanhita/103",
    );
    await user.click(screen.getByRole("button", { name: /Bharatiya Nyaya Sanhita, Section 103/ }));
    expect(screen.getByText(/^Replaces/)).toHaveTextContent("Replaces Indian Penal Code, Section 302.");
    expect(screen.getByRole("link", { name: "Indian Penal Code, Section 302" })).toHaveAttribute(
      "href",
      "/law/Indian%20Penal%20Code/302",
    );
  });
});

describe("returning to a Query", () => {
  const Q = "What is Article 14?";
  const reply = (text: string, extra: object = {}) =>
    sseResponse([
      stageFrame("scope_check", "Checking your question"),
      frame("answer", { ...base, answer: text, ...extra }),
    ]);
  const nothing = { trust_label: "none", citations: [] };

  // The screen as Next keeps it: hidden on leaving for another page, shown again on return.
  const kept = (visible: boolean) => (
    <Activity mode={visible ? "visible" : "hidden"}>
      <AskScreen initialQuery={Q} />
    </Activity>
  );

  async function answeredThen(...next: unknown[]) {
    const fn = vi.fn().mockResolvedValueOnce(reply("First answer."));
    next.forEach((r) => fn.mockResolvedValueOnce(r));
    vi.stubGlobal("fetch", fn);
    const view = render(kept(true));
    await screen.findByText("First answer.");
    return { fn, ...view };
  }

  async function leaveAndReturn(rerender: (ui: React.ReactElement) => void) {
    await act(async () => rerender(kept(false)));
    await act(async () => rerender(kept(true)));
  }

  it("sends nothing when the screen is shown again, and keeps an opened Citation open", async () => {
    const { fn, rerender } = await answeredThen();
    const toggle = screen.getByRole("button", { name: /Constitution of India, Article 14/ });
    await userEvent.click(toggle);
    await leaveAndReturn(rerender);
    expect(screen.getByText("First answer.")).toBeVisible();
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("shows the answer again after a reload without sending the Query", async () => {
    const { fn, unmount } = await answeredThen();
    unmount();
    render(<AskScreen initialQuery={Q} />);
    expect(screen.getByText("First answer.")).toBeInTheDocument();
    expect(screen.getByText("Your answer is ready.")).toBeInTheDocument();
    expect(screen.queryByRole("status", { name: /progress/i })).not.toBeInTheDocument();
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("waits for Clerk before deciding whether a reloaded Query needs sending", async () => {
    const { fn, unmount } = await answeredThen();
    unmount();
    session.isLoaded = false;
    session.userId = null;
    const { rerender } = render(<AskScreen initialQuery={Q} />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    expect(question()).toHaveTextContent(Q);
    session.isLoaded = true;
    session.userId = "user_1";
    rerender(<AskScreen initialQuery={Q} />);
    expect(screen.getByText("First answer.")).toBeInTheDocument();
    expect(screen.queryByText("Loading…")).not.toBeInTheDocument();
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("does not show one user's answer to another", async () => {
    const { fn, rerender } = await answeredThen(reply("Their own answer."));
    session.userId = "user_2";
    await act(async () => rerender(kept(true)));
    expect(await screen.findByText("Their own answer.")).toBeInTheDocument();
    expect(screen.queryByText("First answer.")).not.toBeInTheDocument();
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it("restarts a request that leaving interrupted, with its Stages once each", async () => {
    const first = controlledResponse();
    const second = controlledResponse();
    const fn = vi.fn().mockResolvedValueOnce(first.res).mockResolvedValueOnce(second.res);
    vi.stubGlobal("fetch", fn);
    const { rerender } = render(kept(true));
    first.push(stageFrame("scope_check", "Checking your question"));
    await screen.findByText("Checking your question");
    await act(async () => rerender(kept(false)));
    expect(fn.mock.calls[0][1].signal.aborted).toBe(true);
    await act(async () => rerender(kept(true)));
    await waitFor(() => expect(fn).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole("listitem")).not.toBeInTheDocument();
    second.push(stageFrame("scope_check", "Checking your question"));
    await waitFor(() => expect(screen.getAllByRole("listitem")).toHaveLength(1));
    second.push(frame("answer", base));
    second.close();
    expect(await screen.findByText("From statute text")).toBeInTheDocument();
  });

  it("restarts a request that a reload interrupted", async () => {
    const fn = vi
      .fn()
      .mockReturnValueOnce(new Promise(() => {}))
      .mockResolvedValueOnce(reply("First answer."));
    vi.stubGlobal("fetch", fn);
    const { unmount } = render(<AskScreen initialQuery={Q} />);
    await waitFor(() => expect(fn).toHaveBeenCalledTimes(1));
    unmount();
    render(<AskScreen initialQuery={Q} />);
    expect(await screen.findByText("First answer.")).toBeInTheDocument();
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it("leaves a failed request failed on return, until Try again", async () => {
    const fn = vi.fn().mockResolvedValue({ ok: false, status: 503 });
    vi.stubGlobal("fetch", fn);
    const { rerender } = render(kept(true));
    await screen.findByRole("alert");
    await leaveAndReturn(rerender);
    expect(screen.getByRole("alert")).toHaveTextContent(/unavailable/i);
    expect(screen.getByRole("alert")).not.toHaveTextContent(/earlier answer/i);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("keeps the shown answer while the same Query is asked again, then replaces it", async () => {
    const again = controlledResponse();
    const { fn } = await answeredThen(again.res);
    await askAgain();
    expect(screen.getByRole("status", { name: /progress/i })).toBeInTheDocument();
    expect(screen.getByText("First answer.")).toBeInTheDocument();
    expect(screen.queryByText("Your answer is ready.")).not.toBeInTheDocument();
    again.push(frame("answer", { ...base, answer: "Newer answer." }));
    again.close();
    expect(await screen.findByText("Newer answer.")).toBeInTheDocument();
    expect(screen.queryByText("First answer.")).not.toBeInTheDocument();
    expect(screen.getByText("Your answer is ready.")).toBeInTheDocument();
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it.each([
    ["the service refuses it", () => ({ ok: false, status: 503 })],
    ["the daily limit is reached", () => ({ ok: false, status: 429 })],
    ["a Stage fails", () => sseResponse([frame("error", { stage: "generation", message: "x" })])],
    ["the stream drops", () => sseResponse([stageFrame("scope_check", "Checking")])],
    ["it finds no source", () => reply("Cannot answer.", nothing)],
  ])("keeps the shown answer, also after a reload, when a repeat fails because %s", async (_, res) => {
    const { fn, unmount } = await answeredThen(res());
    await askAgain();
    expect(await screen.findByRole("alert")).toHaveTextContent("Your earlier answer is still shown below.");
    expect(screen.getByText("First answer.")).toBeInTheDocument();
    expect(screen.queryByText("Cannot answer.")).not.toBeInTheDocument();
    expect(screen.queryByText("Your answer is ready.")).not.toBeInTheDocument();
    unmount();
    render(<AskScreen initialQuery={Q} />);
    expect(screen.getByText("First answer.")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it("keeps the shown answer when the network or the session is lost during a repeat", async () => {
    const { fn } = await answeredThen();
    fn.mockRejectedValueOnce(new TypeError("fail"));
    await askAgain();
    expect(await screen.findByRole("alert")).toHaveTextContent(/could not reach.*earlier answer/i);
    fn.mockImplementationOnce(async () => {
      session.isSignedIn = false;
      session.userId = null;
      return { ok: false, status: 401 };
    });
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() =>
      expect(within(screen.getByRole("alert")).getByRole("button", { name: "Sign in" })).toBeInTheDocument(),
    );
    expect(screen.getByText("First answer.")).toBeInTheDocument();
  });

  it("replaces a reply that found no source when a repeat does better", async () => {
    const fn = vi
      .fn()
      .mockResolvedValueOnce(reply("Cannot answer.", nothing))
      .mockResolvedValueOnce(reply("Found it."));
    vi.stubGlobal("fetch", fn);
    render(<AskScreen initialQuery={Q} />);
    await screen.findByText("Cannot answer.");
    await askAgain();
    expect(await screen.findByText("Found it.")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("still returns to an answer when the browser refuses to store it", async () => {
    session.userId = "user_without_storage";
    const setItem = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("full", "QuotaExceededError");
    });
    try {
      const { fn, unmount } = await answeredThen();
      unmount();
      render(<AskScreen initialQuery={Q} />);
      expect(screen.getByText("First answer.")).toBeInTheDocument();
      expect(fn).toHaveBeenCalledTimes(1);
    } finally {
      setItem.mockRestore();
    }
  });

  it("sends the Query when what was stored cannot be read", async () => {
    window.sessionStorage.setItem("legallens.ask.answers.v1", "{oops");
    const { fn } = await answeredThen();
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("keeps only the latest 20 answers", async () => {
    const fn = vi.fn().mockImplementation(async () => reply("An answer."));
    vi.stubGlobal("fetch", fn);
    const { rerender } = render(<AskScreen initialQuery="q0" />);
    for (let i = 0; i <= 20; i++) {
      rerender(<AskScreen initialQuery={`q${i}`} />);
      await screen.findByText("An answer.");
    }
    expect(fn).toHaveBeenCalledTimes(21);
    rerender(<AskScreen initialQuery="q1" />);
    expect(screen.getByText("An answer.")).toBeInTheDocument();
    expect(fn).toHaveBeenCalledTimes(21);
    rerender(<AskScreen initialQuery="q0" />);
    await screen.findByText("An answer.");
    expect(fn).toHaveBeenCalledTimes(22);
  });
});

describe("the folded question", () => {
  const answered = async () => {
    const fn = mockFetch({ ok: true, status: 200, body: base });
    render(<AskScreen initialQuery="What is Article 14?" />);
    await screen.findByText("From statute text");
    return { fn, user: userEvent.setup() };
  };

  it("stands in for the form once a Query is asked", async () => {
    await answered();
    expect(question()).toHaveTextContent("What is Article 14?");
    expect(question()).toHaveAttribute("lang", "en");
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ask" })).not.toBeInTheDocument();
  });

  it("opens the form on the question with Edit, keeping the answer", async () => {
    const { user } = await answered();
    await user.click(screen.getByRole("button", { name: "Edit question" }));
    expect(screen.getByRole("textbox")).toHaveValue("What is Article 14?");
    expect(screen.getByRole("textbox")).toHaveFocus();
    expect(screen.getByText(/Equality before the law/)).toBeInTheDocument();
  });

  it("drops the edit on Cancel", async () => {
    const { fn, user } = await answered();
    await user.click(screen.getByRole("button", { name: "Edit question" }));
    await user.type(screen.getByRole("textbox"), " and 15?");
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(question()).toHaveTextContent("What is Article 14?");
    expect(screen.getByRole("button", { name: "Edit question" })).toHaveFocus();
    await user.click(screen.getByRole("button", { name: "Edit question" }));
    expect(screen.getByRole("textbox")).toHaveValue("What is Article 14?");
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("opens an empty form for another question", async () => {
    const { user } = await answered();
    await user.click(screen.getByRole("button", { name: "Ask another question" }));
    expect(screen.getByRole("textbox")).toHaveValue("");
    expect(screen.getByRole("textbox")).toHaveFocus();
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
  });
});

describe("what was checked", () => {
  it("says how many Citations were checked", async () => {
    mockFetch({ ok: true, status: 200, body: base });
    await ask();
    expect(await screen.findByText("1 Citation checked against the statute text")).toBeInTheDocument();
  });

  it("claims no check for an answer with no Citations", async () => {
    mockFetch({ ok: true, status: 200, body: { ...base, trust_label: "fallback", citations: [] } });
    await ask();
    await screen.findByText(/less reliable/i);
    expect(screen.queryByText(/checked against the statute text/)).not.toBeInTheDocument();
  });
});

describe("repealed mentions", () => {
  const current = {
    ...base.citations[0],
    act: "Bharatiya Nyaya Sanhita",
    number: "318",
    supersedes: "Indian Penal Code 420",
  };
  const old = {
    ...base.citations[0],
    act: "Indian Penal Code",
    number: "420",
    status: "repealed",
    superseded_by: "Bharatiya Nyaya Sanhita 318",
  };
  const answered = async (answer: string, citations: object[], extra: object = {}) => {
    mockFetch({ ok: true, status: 200, body: { ...base, answer, citations, ...extra } });
    const user = await ask();
    await screen.findByRole("button", { name: "Copy answer" });
    return { user, text: screen.getByRole("region", { name: "Answer" }) };
  };

  it("strikes them out and names the replacement where each is first named", async () => {
    const { text } = await answered("IPC 420 covered cheating.\n\nIPC 420 is gone.", [old, current]);
    expect([...text.querySelectorAll("p s")].map((s) => s.textContent)).toEqual(["IPC 420", "IPC 420"]);
    expect(text).toHaveTextContent("IPC 420 (repealed, now BNS 318) covered cheating.");
    expect(text).toHaveTextContent("IPC 420 (repealed) is gone.");
    expect(text.textContent!.match(/now BNS 318/g)).toHaveLength(1);
  });

  it("goes to the replacement's card from its name", async () => {
    const { user, text } = await answered("IPC 420 covered cheating.", [old, current]);
    await user.click(within(text).getByRole("button", { name: "BNS 318" }));
    expect(screen.getByRole("button", { name: /Bharatiya Nyaya Sanhita, Section 318/ })).toHaveFocus();
  });

  it("knows a repealed Provision from the one that replaced it, though it is not cited", async () => {
    const { text } = await answered("IPC 420 covered cheating.", [current]);
    expect(text.querySelector("p s")).toHaveTextContent("IPC 420");
    expect(text).toHaveTextContent("IPC 420 (repealed, now BNS 318)");
    expect(within(text).queryByRole("button", { name: "IPC 420" })).not.toBeInTheDocument();
  });

  it("says it in Hindi in a Hindi answer", async () => {
    const { text } = await answered("IPC 420 धोखाधड़ी पर था।", [old, current], { answer_language: "hi" });
    expect(text).toHaveTextContent("IPC 420 (निरस्त, अब BNS 318)");
  });

  it("leaves an in-force mention as it was", async () => {
    const { text } = await answered("BNS 318 covers cheating.", [current]);
    expect(text.querySelector("p s")).toBeNull();
  });
});

describe("Back to answer", () => {
  const jumped = async () => {
    mockFetch({ ok: true, status: 200, body: { ...base, answer: "See Article 14." } });
    const user = await ask();
    const mention = await screen.findByRole("button", { name: "Article 14" });
    expect(screen.queryByRole("button", { name: "Back to answer" })).not.toBeInTheDocument();
    await user.click(mention);
    return { user, mention };
  };

  it("returns to the mention that was followed", async () => {
    const { user, mention } = await jumped();
    await user.tab();
    expect(screen.getByRole("button", { name: "Back to answer" })).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(mention).toHaveFocus();
    expect(screen.queryByRole("button", { name: "Back to answer" })).not.toBeInTheDocument();
  });

  it("goes away on Stay here, leaving focus on the card", async () => {
    const { user } = await jumped();
    await user.click(screen.getByRole("button", { name: "Stay here" }));
    expect(screen.queryByRole("button", { name: "Back to answer" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Constitution of India, Article 14/ })).toHaveFocus();
  });

  it("is not offered when a card is opened where it is", async () => {
    mockFetch({ ok: true, status: 200, body: base });
    const user = await ask();
    await user.click(await screen.findByRole("button", { name: /Constitution of India, Article 14/ }));
    expect(screen.queryByRole("button", { name: "Back to answer" })).not.toBeInTheDocument();
  });
});
