import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ContractView from "./contract-view";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

const getToken = vi.fn();
vi.mock("@clerk/nextjs", () => ({ useAuth: () => ({ getToken }) }));

const CONTRACT = {
  id: "c1",
  title: "Residential rent agreement",
  created_at: "2026-03-01T10:00:00Z",
  page_count: 3,
  clause_count: 2,
  clauses: [
    { number: "0", heading: "", text: "RENT AGREEMENT between Asha Rao and Ravi Kumar." },
    { number: "7.2", heading: "", text: "7.2 Notice is two months." },
  ],
  conversations: [],
};

// A "Your Contract, Clause 2" label, whose numbers are links inside it.
const where = (text: string) =>
  screen.getByText((_, el) => el?.tagName === "SPAN" && el.classList.contains("text-sm") && el.textContent === text);

beforeEach(() => getToken.mockResolvedValue("tok"));
afterEach(() => vi.unstubAllGlobals());

function stub(res: { ok: boolean; status: number; json?: () => unknown }) {
  const fn = vi.fn().mockResolvedValue(res);
  vi.stubGlobal("fetch", fn);
  return fn;
}

it("shows the Contract's title and each Clause with its number and verbatim text", async () => {
  const fn = stub({ ok: true, status: 200, json: async () => CONTRACT });
  render(<ContractView id="c1" />);
  expect(await screen.findByRole("heading", { name: "Residential rent agreement" })).toBeInTheDocument();
  expect(screen.getByText("Clause 7.2")).toBeInTheDocument();
  expect(screen.getByText("7.2 Notice is two months.")).toBeInTheDocument();
  expect(screen.getByText("Recitals and parties")).toBeInTheDocument(); // Clause 0
  expect(fn.mock.calls[0][0]).toMatch(/\/contracts\/c1$/);
  expect(fn.mock.calls[0][1].headers.Authorization).toBe("Bearer tok");
});

it("shows when the Contract was uploaded and how long it is", async () => {
  stub({ ok: true, status: 200, json: async () => CONTRACT });
  render(<ContractView id="c1" />);
  expect(await screen.findByText("Uploaded 1 Mar 2026 · about 3 pages · 2 Clauses")).toBeInTheDocument();
});

it("names the tab after the Contract, and gives the old name back on leaving", async () => {
  document.title = "Contract | LegalLens";
  stub({ ok: true, status: 200, json: async () => CONTRACT });
  const { unmount } = render(<ContractView id="c1" />);
  await waitFor(() => expect(document.title).toBe("Residential rent agreement | LegalLens"));
  // Next writes the route's own title again on a return to the page.
  document.title = "Contract | LegalLens";
  await waitFor(() => expect(document.title).toBe("Residential rent agreement | LegalLens"));
  unmount();
  expect(document.title).toBe("Contract | LegalLens");
});

it("settles on a tab name when the Contract's title has repeated spaces", async () => {
  document.title = "Contract | LegalLens";
  stub({ ok: true, status: 200, json: async () => ({ ...CONTRACT, title: "Rent  agreement " }) });
  const { unmount } = render(<ContractView id="c1" />);
  await waitFor(() => expect(document.title).toBe("Rent agreement | LegalLens"));
  const write = vi.spyOn(document, "title", "set");
  // Any later change to <head> wakes the watch, which must find nothing to write.
  const meta = document.head.appendChild(document.createElement("meta"));
  await new Promise((resolve) => setTimeout(resolve));
  expect(write).not.toHaveBeenCalled();
  write.mockRestore();
  meta.remove();
  unmount();
  expect(document.title).toBe("Contract | LegalLens");
});

it("offers Hindi under the title, as a way to the question box", async () => {
  Element.prototype.scrollIntoView = vi.fn();
  stub({ ok: true, status: 200, json: async () => CONTRACT });
  render(<ContractView id="c1" />);
  const link = await screen.findByRole("link", { name: /हिंदी में भी पूछ सकते हैं/ });
  expect(link).toHaveAttribute("lang", "hi");
  await userEvent.click(link);
  expect(screen.getByRole("heading", { name: "Ask about this Contract" })).toHaveFocus();
});

it("says the Contract was not found on a 404 (someone else's looks the same)", async () => {
  stub({ ok: false, status: 404 });
  render(<ContractView id="nope" />);
  expect(await screen.findByRole("alert")).toHaveTextContent(/could not find that contract/i);
});

it("explains a failed load", async () => {
  stub({ ok: false, status: 503 });
  render(<ContractView id="c1" />);
  expect(await screen.findByRole("alert")).toHaveTextContent(/unavailable/i);
});

const BRIEF = {
  parties: ["Asha Rao (Landlord)", "Ravi Kumar (Tenant)"],
  purpose: "Rent of a flat in Pune for eleven months.",
  key_terms: [{ label: "Monthly rent", value: "Rs. 20,000", clause: "2" }],
  obligations: [
    {
      party: "Tenant",
      obligations: [{ text: "Pay the rent by the 5th.", clauses: ["2", "2.1"] }],
    },
  ],
  flagged_clauses: [
    {
      clause_reference: { number: "3", text: "3. Deposit\nThe Tenant pays Rs. 1,00,000." },
      how_it_differs: "The deposit is more than the Model Tenancy Act provides.",
      citations: [
        {
          act: "Model Tenancy Act",
          chapter: "Chapter II",
          number: "11",
          status: "model" as const,
          text: "The security deposit shall not exceed two months' rent.",
          superseded_by: null,
          supersedes: null,
        },
      ],
    },
  ],
};

async function renderWithBrief(brief: unknown) {
  stub({ ok: true, status: 200, json: async () => ({ ...CONTRACT, brief }) });
  render(<ContractView id="c1" />);
  await screen.findByRole("heading", { name: "Residential rent agreement" });
}

it("shows every section of the brief", async () => {
  await renderWithBrief(BRIEF);
  expect(screen.getByRole("heading", { name: "Parties" })).toBeInTheDocument();
  expect(screen.getByText("Asha Rao (Landlord)")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "What it is for" })).toBeInTheDocument();
  expect(screen.getByText(/Rent of a flat in Pune/)).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Key terms" })).toBeInTheDocument();
  expect(screen.getByText("Monthly rent")).toBeInTheDocument();
  expect(screen.getByText("Rs. 20,000")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "What each party must do" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Tenant" })).toBeInTheDocument();
  expect(screen.getByText("Pay the rent by the 5th.")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Flagged clauses" })).toBeInTheDocument();
});

it("defines a Flagged clause and puts the caveats at the head of the brief", async () => {
  await renderWithBrief(BRIEF);
  expect(screen.getByText(/A Flagged clause differs from what Indian law provides/)).toBeInTheDocument();
  const caveats = screen.getByText(/not legal advice/i).parentElement!;
  expect(caveats).toHaveTextContent(/Check them against your own copy/);
  const parties = screen.getByRole("heading", { name: "Parties" });
  expect(caveats.compareDocumentPosition(parties)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
});

it("labels Clause references as your Contract's", async () => {
  await renderWithBrief(BRIEF);
  expect(where("Your Contract, Clause 2")).toBeInTheDocument(); // the key term
  expect(where("Your Contract, Clauses 2, 2.1")).toBeInTheDocument(); // the obligation
  expect(where("Your Contract, Clause 3")).toBeInTheDocument(); // the flag
});

it("shows a Flagged clause's own text, how it differs, and its Citation with a link to /law", async () => {
  await renderWithBrief(BRIEF);
  expect(screen.getByText(/The Tenant pays Rs\. 1,00,000\./)).toBeInTheDocument();
  expect(screen.getByText(/more than the Model Tenancy Act provides/)).toBeInTheDocument();
  // The Citation's text waits until it is asked for.
  expect(screen.queryByText(/security deposit shall not exceed two months/)).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Model Tenancy Act, Section 11/ }));
  expect(screen.getByText(/security deposit shall not exceed two months/)).toBeInTheDocument();
  const link = screen.getByRole("link", { name: /Open full Provision: Model Tenancy Act, Section 11/ });
  expect(link).toHaveAttribute("href", "/law/Model%20Tenancy%20Act/11");
  expect(screen.getByText(/not law in force by\s+itself/i)).toBeInTheDocument();
});

it("shows a Provision cited by two flags once, and leads back to it from the second", async () => {
  Element.prototype.scrollIntoView = vi.fn();
  const [flag] = BRIEF.flagged_clauses;
  const second = { ...flag, clause_reference: { number: "4", text: "4. Refund\nNo refund." } };
  await renderWithBrief({ ...BRIEF, flagged_clauses: [flag, second] });
  expect(screen.getAllByRole("link", { name: /Open full Provision/ })).toHaveLength(1);
  expect(screen.getAllByText(/not law in force by\s+itself/i)).toHaveLength(1); // the model Act warning
  const back = screen.getByRole("link", { name: "Text shown above, under Clause 3: Model Tenancy Act, Section 11" });
  await userEvent.click(back);
  const card = screen.getByRole("button", { name: /Model Tenancy Act, Section 11/ });
  expect(card).toHaveAttribute("aria-expanded", "true");
  expect(card).toHaveFocus();
  expect(screen.getAllByText(/security deposit shall not exceed two months/)).toHaveLength(1);
});

it("shows a Clause's title once, in its heading, and keeps every other line", async () => {
  const clauses = [
    { number: "1", heading: "Premises and term", text: "1. Premises and term\n" },
    { number: "2", heading: "Rent", text: "2. Rent\nThe Tenant pays monthly." },
    { number: "3", heading: "The Tenant shall pay a deposit of", text: "3. The Tenant shall pay a deposit of\nRs. 1,00,000 on signing." },
  ];
  stub({ ok: true, status: 200, json: async () => ({ ...CONTRACT, clauses }) });
  render(<ContractView id="c1" />);
  expect(await screen.findByRole("heading", { name: /^Clause 1\s*·\s*Premises and term$/ })).toBeInTheDocument();
  const item = (n: string) => document.getElementById(`clause-${n}`)!;
  expect(item("1").querySelector("p")).toBeNull();
  expect(screen.getByRole("heading", { name: /^Clause 2\s*·\s*Rent$/ })).toBeInTheDocument();
  expect(item("2").querySelector("p")).toHaveTextContent(/^The Tenant pays monthly\.$/);
  // A first line that runs on is part of a sentence, so it stays in the text.
  expect(screen.getByRole("heading", { name: "Clause 3" })).toBeInTheDocument();
  expect(item("3").querySelector("p")?.textContent).toBe(clauses[2].text);
});

it("keeps the breaks between a Citation's parts and joins the lines that only wrapped", async () => {
  const [flag] = BRIEF.flagged_clauses;
  const text = "(1) The deposit shall\nbe agreed.\n(2) It shall be refunded.";
  await renderWithBrief({ ...BRIEF, flagged_clauses: [{ ...flag, citations: [{ ...flag.citations[0], text }] }] });
  await userEvent.click(screen.getByRole("button", { name: /Model Tenancy Act, Section 11/ }));
  const quote = document.querySelector("#flagged article blockquote[lang='en']")!;
  expect([...quote.children].map((p) => p.textContent)).toEqual(["(1) The deposit shall be agreed.", "(2) It shall be refunded."]);
});

it("says so when no clause was flagged, and never offers a verdict on signing", async () => {
  await renderWithBrief({ ...BRIEF, flagged_clauses: [] });
  expect(screen.getByText(/No clause was flagged/i)).toBeInTheDocument();
  expect(screen.queryByText(/should sign|do not sign|safe to sign/i)).not.toBeInTheDocument();
});

it("still shows the Clauses of a Contract that has no brief", async () => {
  await renderWithBrief(null);
  expect(screen.queryByRole("heading", { name: "Parties" })).not.toBeInTheDocument();
  expect(screen.getByText("Clause 7.2")).toBeInTheDocument();
});

it("offers Delete, asks for confirmation, then deletes and returns to the list", async () => {
  const fn = vi.fn().mockImplementation(async (_url: string, init?: RequestInit) =>
    init?.method === "DELETE"
      ? { ok: true, status: 204 }
      : { ok: true, status: 200, json: async () => CONTRACT },
  );
  vi.stubGlobal("fetch", fn);
  const user = userEvent.setup();
  render(<ContractView id="c1" />);
  await user.click(await screen.findByRole("button", { name: /delete/i }));
  expect(screen.getByText(/delete this contract\?/i)).toBeInTheDocument();
  expect(fn.mock.calls.filter(([, i]) => i?.method === "DELETE")).toHaveLength(0);
  await user.click(screen.getByRole("button", { name: /yes, delete/i }));
  await waitFor(() => expect(push).toHaveBeenCalledWith("/contracts"));
  const [url, init] = fn.mock.calls.find(([, i]) => i?.method === "DELETE")!;
  expect(url).toMatch(/\/contracts\/c1$/);
  expect(init.headers.Authorization).toBe("Bearer tok");
});

const clause = (number: string, text = `${number}. Text of Clause ${number}.`) => ({ number, heading: "", text });
const LINKED = {
  ...CONTRACT,
  clause_count: 4,
  clauses: [
    clause("2", "2. Rent. Payable subject to Clause 3."),
    clause("2.1"),
    clause("3", "3. Deposit. As defined in clause 3 of the Consumer Protection Act."),
    clause("7(a)"),
  ],
  brief: {
    ...BRIEF,
    purpose: "A lease. See Clauses 2.1 and 7(a), and Clause 99.",
  },
};

describe("Clause links", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/");
    Element.prototype.scrollIntoView = vi.fn();
  });

  async function renderLinked() {
    stub({ ok: true, status: 200, json: async () => LINKED });
    const user = userEvent.setup();
    render(<ContractView id="c1" />);
    await screen.findByRole("heading", { name: "Residential rent agreement" });
    return user;
  }
  const section = (name: string) => screen.getByRole("region", { name });
  const target = (number: string) => document.getElementById(`clause-${number}`)!;

  it("links every number in the brief to its Clause", async () => {
    await renderLinked();
    const hrefs = (name: string) =>
      within(section(name))
        .getAllByRole("link", { name: /^Clause/ })
        .map((a) => a.getAttribute("href"));
    expect(hrefs("Key terms")).toEqual(["#clause-2"]);
    expect(hrefs("What each party must do")).toEqual(["#clause-2", "#clause-2.1"]);
    expect(hrefs("Flagged clauses")).toEqual(["#clause-3"]);
    // Mentions in running text too, but not a number the Contract does not have.
    expect(hrefs("What it is for")).toEqual(["#clause-2.1", "#clause-7(a)"]);
  });

  it("opens a hash link on the Clause it names, once the Contract has loaded", async () => {
    window.history.replaceState(null, "", "/#clause-7(a)");
    await renderLinked();
    await waitFor(() => expect(target("7(a)")).toHaveAttribute("data-current"));
    expect(screen.queryByRole("button", { name: /^Back to/ })).not.toBeInTheDocument();
  });

  it("links a cross-reference in a Clause, but not itself or a clause of an Act", async () => {
    await renderLinked();
    expect(within(target("2")).getByRole("link", { name: "Clause 3" })).toBeInTheDocument();
    expect(within(target("3")).queryByRole("link")).not.toBeInTheDocument();
  });

  it("jumps to the Clause, marks it, and goes back to the link", async () => {
    const user = await renderLinked();
    const link = within(section("Key terms")).getByRole("link", { name: "Clause 2" });
    await user.click(link);
    expect(target("2")).toHaveAttribute("data-current");
    expect(within(target("2")).getByRole("heading")).toHaveFocus();
    await user.tab(); // the way back is the next stop
    expect(screen.getByRole("button", { name: "Back to Key terms" })).toHaveFocus();
    await user.keyboard("{Enter}");
    await waitFor(() => expect(link).toHaveFocus());
    expect(target("2")).not.toHaveAttribute("data-current");
    expect(screen.queryByRole("button", { name: /^Back to/ })).not.toBeInTheDocument();
  });

  it("returns to the start on the browser's Back, after following a cross-reference", async () => {
    const user = await renderLinked();
    const link = within(section("Key terms")).getByRole("link", { name: "Clause 2" });
    await user.click(link);
    await user.click(within(target("2")).getByRole("link", { name: "Clause 3" }));
    expect(target("3")).toHaveAttribute("data-current");
    expect(target("2")).not.toHaveAttribute("data-current");
    expect(screen.getByRole("button", { name: "Back to Key terms" })).toBeInTheDocument();
    window.history.back();
    await waitFor(() => expect(link).toHaveFocus());
    expect(target("3")).not.toHaveAttribute("data-current");
  });

  it("can drop the way back and keep the Clause marked", async () => {
    const user = await renderLinked();
    await user.click(within(section("Key terms")).getByRole("link", { name: "Clause 2" }));
    await user.click(screen.getByRole("button", { name: "Stay here" }));
    expect(screen.queryByRole("button", { name: /^Back to/ })).not.toBeInTheDocument();
    expect(target("2")).toHaveAttribute("data-current");
    expect(within(target("2")).getByRole("heading")).toHaveFocus();
  });
});

describe("the page's order", () => {
  it("has an index under the title, Flagged clauses after the purpose and Delete last", async () => {
    await renderWithBrief(BRIEF);
    expect(screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent)).toEqual([
      "Parties",
      "What it is for",
      "Flagged clauses",
      "Key terms",
      "What each party must do",
      "Ask about this Contract",
      "The Contract, Clause by Clause",
    ]);
    const index = screen.getByRole("navigation", { name: "On this page" });
    expect(within(index).getAllByRole("link").map((a) => [a.textContent, a.getAttribute("href")])).toEqual([
      ["Flagged clauses (1)", "#flagged"],
      ["Key terms", "#terms"],
      ["What each party must do", "#obligations"],
      ["Ask about this Contract", "#ask"],
      ["The Contract", "#contract-text"],
    ]);
    const remove = screen.getByRole("button", { name: /delete/i });
    const last = document.getElementById("contract-text")!;
    expect(last.compareDocumentPosition(remove) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    // Each Clause sits under the Contract's own heading.
    expect(screen.getByRole("heading", { level: 3, name: "Clause 7.2" })).toBeInTheDocument();
  });

  it("moves focus to a section chosen from the index", async () => {
    Element.prototype.scrollIntoView = vi.fn();
    await renderWithBrief(BRIEF);
    await userEvent.setup().click(screen.getByRole("link", { name: "Ask about this Contract" }));
    expect(screen.getByRole("heading", { name: "Ask about this Contract" })).toHaveFocus();
  });

  it("indexes only the parts a Contract without a brief has", async () => {
    await renderWithBrief(null);
    const index = screen.getByRole("navigation", { name: "On this page" });
    expect(within(index).getAllByRole("link")).toHaveLength(2);
  });
});
