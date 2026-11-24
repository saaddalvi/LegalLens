import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
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
};

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

it("labels Clause references as your Contract's", async () => {
  await renderWithBrief(BRIEF);
  expect(screen.getByText("Your Contract, Clause 2")).toBeInTheDocument(); // the key term
  expect(screen.getByText("Your Contract, Clauses 2, 2.1")).toBeInTheDocument(); // the obligation
  expect(screen.getByText("Your Contract, Clause 3")).toBeInTheDocument(); // the flag
});

it("shows a Flagged clause's own text, how it differs, and its Citation with a link to /law", async () => {
  await renderWithBrief(BRIEF);
  expect(screen.getByText(/The Tenant pays Rs\. 1,00,000\./)).toBeInTheDocument();
  expect(screen.getByText(/more than the Model Tenancy Act provides/)).toBeInTheDocument();
  expect(screen.getByText(/security deposit shall not exceed two months/)).toBeInTheDocument();
  const link = screen.getByRole("link", { name: /Open full Provision: Model Tenancy Act, 11/ });
  expect(link).toHaveAttribute("href", "/law/Model%20Tenancy%20Act/11");
  expect(screen.getByText(/not law in force by\s+itself/i)).toBeInTheDocument();
});

it("says so when no clause was flagged, and never offers a verdict on signing", async () => {
  await renderWithBrief({ ...BRIEF, flagged_clauses: [] });
  expect(screen.getByText(/No clause was flagged/i)).toBeInTheDocument();
  expect(screen.queryByText(/should sign|do not sign|safe to sign/i)).not.toBeInTheDocument();
});

it("always shows the disclaimer, with or without a brief", async () => {
  await renderWithBrief(BRIEF);
  expect(screen.getByText(/not legal advice/i)).toBeInTheDocument();
});

it("still shows the Clauses of a Contract that has no brief", async () => {
  await renderWithBrief(null);
  expect(screen.queryByRole("heading", { name: "Parties" })).not.toBeInTheDocument();
  expect(screen.getByText("Clause 7.2")).toBeInTheDocument();
  expect(screen.getByText(/not legal advice/i)).toBeInTheDocument();
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
