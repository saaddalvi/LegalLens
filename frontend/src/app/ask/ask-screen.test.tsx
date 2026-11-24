import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AskScreen from "./ask-screen";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

const getToken = vi.fn();
vi.mock("@clerk/nextjs", () => ({ useAuth: () => ({ getToken }) }));

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

beforeEach(() => getToken.mockResolvedValue("session-token"));

afterEach(() => {
  vi.unstubAllGlobals();
  push.mockReset();
  getToken.mockReset();
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

  it("reveals a long answer within the cap, then shows the Trust label and Citations", async () => {
    await startAnswering({ ...base, answer: longAnswer });
    const section = screen.getByRole("region", { name: "Answer" });
    expect(section).toHaveTextContent(longAnswer);
    expect(screen.queryByText("From statute text")).not.toBeInTheDocument();
    expect(screen.queryByText(/Constitution of India/)).not.toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(screen.queryByText("From statute text")).not.toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(screen.getByText("From statute text")).toBeInTheDocument();
    expect(screen.getByText(/Constitution of India/)).toBeInTheDocument();
  });

  it("shows everything at once when the answer is clicked", async () => {
    await startAnswering({ ...base, answer: longAnswer });
    expect(screen.queryByText("From statute text")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText(/word0/));
    expect(screen.getByText("From statute text")).toBeInTheDocument();
    expect(screen.getByText(/Constitution of India/)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Answer" })).toHaveTextContent(longAnswer);
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
    expect(screen.queryByRole("button", { name: "What does Article 14 say?" })).not.toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });
    expect(screen.getByRole("button", { name: "What does Article 14 say?" })).toBeInTheDocument();
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
    const toggle = screen.getByRole("button", { name: /Bharatiya Nyaya Sanhita, 103/ });
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
    const toggle = screen.getByRole("button", { name: /Bharatiya Nyaya Sanhita, 103A/ });
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
    expect(copied).toContain("- Constitution of India, 14");
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
    const link = await screen.findByRole("link", { name: /Open full Provision: Constitution of India, 14/ });
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
    expect(note).toHaveTextContent("The current law is Bharatiya Nyaya Sanhita 103.");
    expect(within(note).getByRole("link", { name: "Bharatiya Nyaya Sanhita 103" })).toHaveAttribute(
      "href",
      "/law/Bharatiya%20Nyaya%20Sanhita/103",
    );
    await user.click(screen.getByRole("button", { name: /Bharatiya Nyaya Sanhita, 103/ }));
    expect(screen.getByText(/^Replaces/)).toHaveTextContent("Replaces Indian Penal Code 302.");
    expect(screen.getByRole("link", { name: "Indian Penal Code 302" })).toHaveAttribute(
      "href",
      "/law/Indian%20Penal%20Code/302",
    );
  });
});
