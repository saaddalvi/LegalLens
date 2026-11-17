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

function mockFetch(res: { ok: boolean; status: number; body?: unknown }) {
  const fn = vi.fn().mockResolvedValue({
    ok: res.ok,
    status: res.status,
    json: async () => res.body,
  });
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
    expect(screen.getByRole("status", { name: /loading/i })).toBeInTheDocument();
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
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => answer("First answer.") })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => answer("Second answer.") });
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
});
