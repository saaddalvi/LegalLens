import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LandingPage from "./landing-page";
import { CORPUS_ACTS, askHref, EXAMPLE_QUERIES, REPEAL_NOTE } from "@/lib/corpus";
import { TRUST_TEXT } from "@/lib/trust-labels";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

beforeEach(() => push.mockClear());

describe("LandingPage", () => {
  it("shows the disclaimer", () => {
    render(<LandingPage />);
    expect(screen.getAllByText(/not legal advice/i).length).toBeGreaterThan(0);
  });

  it("links English and Hindi example Queries to /ask with the Query URL-encoded", () => {
    render(<LandingPage />);
    for (const q of [...EXAMPLE_QUERIES.en, ...EXAMPLE_QUERIES.hi]) {
      const link = screen.getByRole("link", { name: q });
      expect(link).toHaveAttribute("href", askHref(q));
    }
    const hi = screen.getByRole("link", { name: EXAMPLE_QUERIES.hi[0] });
    expect(hi).toHaveAttribute("lang", "hi");
  });

  it("submits the ask box to /ask with the typed Query, and ignores an empty box", async () => {
    const user = userEvent.setup();
    render(<LandingPage />);
    const box = screen.getByRole("textbox");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    await user.type(box, "   ");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(push).not.toHaveBeenCalled();
    await user.clear(box);
    await user.type(box, "Can I record a call?");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(push).toHaveBeenCalledWith("/ask?q=Can+I+record+a+call%3F");
  });

  it("lists every Act in the Corpus and the repeal note", () => {
    render(<LandingPage />);
    const section = screen.getByRole("region", { name: /what the corpus covers/i });
    for (const act of CORPUS_ACTS) expect(within(section).getByText(act)).toBeInTheDocument();
    expect(within(section).getByText(REPEAL_NOTE)).toBeInTheDocument();
  });

  it("explains each Trust label with the wording used on answers", () => {
    render(<LandingPage />);
    const section = screen.getByRole("region", { name: /trust labels/i });
    for (const text of Object.values(TRUST_TEXT)) {
      expect(within(section).getByText(text)).toBeInTheDocument();
    }
  });

  it("has a direct link to /ask", () => {
    render(<LandingPage />);
    expect(screen.getByRole("link", { name: /go to the asking screen/i })).toHaveAttribute("href", "/ask");
  });
});
