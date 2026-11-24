import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import ContractView from "./contract-view";

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
