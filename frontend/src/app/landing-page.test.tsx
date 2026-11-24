import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LandingPage from "./landing-page";
import { CORPUS_ACTS, askHref, EXAMPLE_QUERIES, lawHref, REPEAL_NOTE, SPECIMEN } from "@/lib/corpus";
import { TRUST_EXPLANATION, TRUST_TEXT } from "@/lib/trust-labels";

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

  it("links the hero specimen to the answer for its Query", () => {
    render(<LandingPage />);
    const specimen = screen.getByRole("link", { name: `See the full answer to: ${SPECIMEN.query}` });
    expect(specimen).toHaveAttribute("href", askHref(SPECIMEN.query));
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

  it("links each Act to its Provisions", () => {
    render(<LandingPage />);
    const section = screen.getByRole("region", { name: /what the corpus covers/i });
    for (const act of CORPUS_ACTS) {
      const link = within(section).getByText(act).closest("a");
      expect(link).toHaveAttribute("href", lawHref(act));
    }
  });

  it("explains each Trust label with the wording used on answers", () => {
    render(<LandingPage />);
    const section = screen.getByRole("region", { name: /trust labels/i });
    for (const text of Object.values(TRUST_TEXT)) {
      expect(within(section).getByText(text)).toBeInTheDocument();
    }
  });

  it("explains the Contract-backed Trust labels too", () => {
    render(<LandingPage />);
    const section = screen.getByRole("region", { name: /trust labels/i });
    for (const label of ["contract", "contract_and_corpus", "contract_and_fallback", "contract_corpus_and_fallback"] as const) {
      expect(within(section).getByText(TRUST_TEXT[label])).toBeInTheDocument();
      expect(within(section).getByText(TRUST_EXPLANATION[label])).toBeInTheDocument();
    }
  });

  it("has a direct link to /ask", () => {
    render(<LandingPage />);
    expect(screen.getByRole("link", { name: /go to the asking screen/i })).toHaveAttribute("href", "/ask");
  });

  it("offers a Contract upload path beside the ask box, saying only English Contracts are accepted", () => {
    render(<LandingPage />);
    expect(screen.getByRole("link", { name: "Upload a Contract" })).toHaveAttribute("href", "/contracts");
    expect(screen.getAllByText(/only english contracts are accepted/i).length).toBeGreaterThan(0);
  });

  it("adds a Contract lane to How it works", () => {
    render(<LandingPage />);
    const section = screen.getByRole("region", { name: /how it works/i });
    expect(within(section).getByText("Or upload a Contract")).toBeInTheDocument();
    expect(within(section).getByText(/Flagged clause/)).toBeInTheDocument();
  });

  it("sets the Hindi line in Hindi", () => {
    render(<LandingPage />);
    expect(screen.getByText(/हिंदी में भी पूछिए/)).toHaveAttribute("lang", "hi");
  });

  it("tells a screen reader when the ask box is submitted empty, and clears the hint on typing", async () => {
    const user = userEvent.setup();
    render(<LandingPage />);
    const box = screen.getByRole("textbox");
    expect(box).toBeRequired();
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(screen.getByRole("status")).toHaveTextContent(/type your question first/i);
    expect(box).toBeInvalid();
    await user.type(box, "x");
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
  });

  it("shows three Trust labels and tucks the five Contract and mixed ones behind a disclosure", () => {
    render(<LandingPage />);
    const section = screen.getByRole("region", { name: /trust labels/i });
    const summary = within(section).getByText(/labels for contracts and mixed sources \(5\)/i).closest("details");
    expect(summary).not.toHaveAttribute("open");
    expect(summary).toContainElement(within(section).getByText(TRUST_TEXT.contract));
    expect(summary).not.toContainElement(within(section).getByText(TRUST_TEXT.corpus));
    expect(summary).not.toContainElement(within(section).getByText(TRUST_TEXT.none));
  });

  it("shows six Acts and puts the rest, repealed last, behind See all 15", () => {
    render(<LandingPage />);
    const section = screen.getByRole("region", { name: /what the corpus covers/i });
    const more = within(section).getByText(/see all 15 acts/i).closest("details")!;
    expect(more).not.toHaveAttribute("open");
    expect(more).not.toContainElement(within(section).getByText("Bharatiya Nyaya Sanhita"));
    const links = within(more).getAllByRole("link", { hidden: true });
    expect(links).toHaveLength(9);
    expect(links.slice(-3).map((l) => l.textContent)).toEqual([
      "Indian Penal Codenow BNS",
      "Code of Criminal Procedurenow BNSS",
      "Indian Evidence Actnow BSA",
    ]);
  });
});
