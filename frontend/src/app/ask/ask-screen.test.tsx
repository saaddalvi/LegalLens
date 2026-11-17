import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import AskScreen from "./ask-screen";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

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

async function ask() {
  const user = userEvent.setup();
  render(<AskScreen />);
  await user.type(screen.getByLabelText(/ask a question/i), "What is Article 14?");
  await user.click(screen.getByRole("button", { name: "Ask" }));
  return user;
}

afterEach(() => {
  vi.unstubAllGlobals();
  push.mockReset();
});

describe("AskScreen", () => {
  it("shows the disclaimer, Trust label and Citations", async () => {
    mockFetch({ ok: true, status: 200, body: base });
    await ask();
    expect(screen.getByText(/not legal advice/i)).toBeInTheDocument();
    expect(await screen.findByText("From statute text")).toBeInTheDocument();
    expect(screen.getByText(/Constitution of India, 14/)).toBeInTheDocument();
  });

  it("expands and collapses a Citation", async () => {
    mockFetch({ ok: true, status: 200, body: base });
    const user = await ask();
    const toggle = await screen.findByRole("button", { name: /Constitution of India, 14/ });
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
    const toggle = await screen.findByRole("button", { name: /Model Tenancy Act, 11/ });
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
    expect(screen.getByRole("button", { name: /thinking/i })).toBeDisabled();
    expect(screen.getByRole("status", { name: /progress/i })).toBeInTheDocument();
  });

  it("explains rate limits", async () => {
    mockFetch({ ok: false, status: 429 });
    await ask();
    expect(await screen.findByRole("alert")).toHaveTextContent(/too many questions/i);
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
    expect(screen.getByLabelText(/ask a question/i)).toHaveValue("What is Article 14?");
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
    expect(screen.getByLabelText(/ask a question/i)).toHaveValue("second");
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
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/could not reach/i);
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
