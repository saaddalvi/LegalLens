import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ActView from "./act-view";
import ActsView from "./acts-view";
import ProvisionView from "./provision-view";
import type { Provision } from "@/lib/ask-types";

const ipc302: Provision = {
  act: "Indian Penal Code",
  chapter: "Chapter XVI",
  number: "302",
  status: "repealed",
  text: "Whoever commits murder shall be punished with death.\nOr imprisonment for life.",
  superseded_by: "Bharatiya Nyaya Sanhita 103",
  supersedes: null,
};

const bns103: Provision = {
  act: "Bharatiya Nyaya Sanhita",
  chapter: "Chapter VI",
  number: "103",
  status: "in_force",
  text: "(1) Whoever commits murder shall be punished with death or imprisonment for life.",
  superseded_by: null,
  supersedes: "Indian Penal Code 302",
};

describe("ProvisionView", () => {
  it("shows a repealed Provision's warning with a link to the law that replaced it", () => {
    render(<ProvisionView provision={ipc302} />);
    const note = screen.getAllByRole("note").find((n) => /has been repealed/.test(n.textContent ?? ""))!;
    expect(note).toHaveTextContent("This Provision has been repealed. The current law is Bharatiya Nyaya Sanhita, Section 103.");
    expect(within(note).getByRole("link", { name: "Bharatiya Nyaya Sanhita, Section 103" })).toHaveAttribute(
      "href",
      "/law/Bharatiya%20Nyaya%20Sanhita/103",
    );
  });

  it("links an in-force Provision back to the one it replaced", () => {
    render(<ProvisionView provision={bns103} />);
    expect(screen.getByRole("link", { name: "Indian Penal Code, Section 302" })).toHaveAttribute(
      "href",
      "/law/Indian%20Penal%20Code/302",
    );
    expect(screen.queryByText(/has been repealed/)).not.toBeInTheDocument();
  });

  it("flags a model Act Provision as not in force by itself", () => {
    render(
      <ProvisionView
        provision={{ ...bns103, act: "Model Tenancy Act", number: "11", status: "model", supersedes: null }}
      />,
    );
    expect(screen.getAllByRole("note")[0]).toHaveTextContent(/model Act, a template/);
  });

  it("shows the full text and says it is English", () => {
    render(<ProvisionView provision={ipc302} />);
    const quote = screen.getByText(/Whoever commits murder/);
    expect(quote.textContent).toBe(ipc302.text);
    expect(quote).toHaveAttribute("lang", "en");
  });

  it("lets the text wrap freely, because its line breaks come from the source PDF's layout", () => {
    // Breaking at every stored newline split sentences mid-way ("and shall also be / liable to fine").
    render(<ProvisionView provision={ipc302} />);
    expect(screen.getByText(/Whoever commits murder/).className).not.toMatch(/whitespace-pre/);
  });

  it("links up to its Act and to all Acts", () => {
    render(<ProvisionView provision={ipc302} />);
    const crumbs = screen.getByRole("navigation", { name: "Breadcrumb" });
    expect(within(crumbs).getByRole("link", { name: "All Acts" })).toHaveAttribute("href", "/law");
    expect(within(crumbs).getByRole("link", { name: "Indian Penal Code" })).toHaveAttribute(
      "href",
      "/law/Indian%20Penal%20Code",
    );
  });

  it("offers to ask about the Provision, starting an answer at once", () => {
    render(<ProvisionView provision={bns103} />);
    const link = screen.getByRole("link", { name: "Ask LegalLens about this Provision" });
    const href = link.getAttribute("href")!;
    expect(href.startsWith("/ask?")).toBe(true);
    expect(new URLSearchParams(href.slice(5)).get("q")).toBe(
      "What does Bharatiya Nyaya Sanhita 103 say?",
    );
  });
});

describe("ActView", () => {
  const index = {
    act: "Indian Penal Code",
    provisions: [
      { number: "300", chapter: "Chapter XVI", status: "repealed" as const, snippet: "Murder." },
      { number: "302", chapter: "Chapter XVI", status: "repealed" as const, snippet: "Punishment for murder." },
      { number: "375", chapter: "Chapter XVI-A", status: "in_force" as const, snippet: "Rape." },
    ],
  };

  it("groups consecutive Provisions under their chapter", () => {
    render(<ActView index={index} />);
    const first = screen.getByRole("region", { name: "Chapter XVI" });
    expect(within(first).getAllByRole("listitem")).toHaveLength(2);
    expect(within(screen.getByRole("region", { name: "Chapter XVI-A" })).getAllByRole("listitem")).toHaveLength(1);
  });

  it("links each Provision to its full text and marks repealed ones", () => {
    render(<ActView index={index} />);
    const link = screen.getByRole("link", { name: /302.*Punishment for murder/ });
    expect(link).toHaveAttribute("href", "/law/Indian%20Penal%20Code/302");
    expect(link).toHaveTextContent("repealed");
    expect(screen.getByRole("link", { name: /375/ })).not.toHaveTextContent("repealed");
  });

  it("says how many Provisions the Act has", () => {
    render(<ActView index={index} />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Indian Penal Code");
    expect(screen.getByText("3 Provisions")).toBeInTheDocument();
  });
});

describe("ActsView", () => {
  it("lists each Act with its count, linking to it", () => {
    render(
      <ActsView
        acts={[
          { act: "Constitution of India", provisions: 499 },
          { act: "Indian Penal Code", provisions: 575 },
        ]}
      />,
    );
    const link = screen.getByRole("link", { name: /Constitution of India/ });
    expect(link).toHaveAttribute("href", "/law/Constitution%20of%20India");
    expect(link).toHaveTextContent("499 Provisions");
  });

  it("says what replaced a repealed Act", () => {
    render(<ActsView acts={[{ act: "Indian Penal Code", provisions: 575 }]} />);
    expect(screen.getByRole("link", { name: /Indian Penal Code/ })).toHaveTextContent("now BNS");
  });
});
