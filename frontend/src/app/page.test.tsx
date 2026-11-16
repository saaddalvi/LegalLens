import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import Home from "./page";

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
  render(<Home />);
  await user.type(screen.getByLabelText(/ask a question/i), "What is Article 14?");
  await user.click(screen.getByRole("button", { name: "Ask" }));
  return user;
}

afterEach(() => vi.unstubAllGlobals());

describe("Home", () => {
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
});
