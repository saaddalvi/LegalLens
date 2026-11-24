import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ContractsScreen from "./contracts-screen";

const getToken = vi.fn();
vi.mock("@clerk/nextjs", () => ({ useAuth: () => ({ getToken }) }));

const enc = new TextEncoder();
const frame = (name: string, data: unknown) => `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`;
const stage = (id: string, label: string) => frame("stage", { id, label });

function sse(chunks: string[]) {
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

const RENT = {
  id: "c1",
  title: "Residential rent agreement",
  created_at: "2026-03-01T10:00:00Z",
  page_count: 3,
  clause_count: 12,
};

const STAGES =
  stage("reading", "Reading your file") +
  stage("contract_check", "Checking that it is a Contract in English") +
  stage("splitting", "Finding the Clauses") +
  stage("indexing", "Indexing the Clauses");

// Stubs the API: the list starts as `initial` and becomes `afterUpload` once an upload has gone.
function stubApi(opts: {
  initial?: unknown[];
  afterUpload?: unknown[];
  upload?: () => unknown;
  listStatus?: number;
}) {
  let uploaded = false;
  const fn = vi.fn().mockImplementation(async (url: string, init?: RequestInit) => {
    if (init?.method === "POST") {
      uploaded = true;
      return opts.upload!();
    }
    if (opts.listStatus) return { ok: false, status: opts.listStatus };
    const list = uploaded ? (opts.afterUpload ?? opts.initial ?? []) : (opts.initial ?? []);
    return { ok: true, status: 200, json: async () => list };
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

beforeEach(() => getToken.mockResolvedValue("session-token"));
afterEach(() => vi.unstubAllGlobals());

async function pasteAndUpload(text = "1. Term\nEleven months.\n2. Rent\nRs. 5.") {
  const user = userEvent.setup();
  render(<ContractsScreen />);
  await user.click(screen.getByRole("tab", { name: /paste text/i }));
  await user.type(screen.getByLabelText(/paste the contract/i), text);
  await user.click(screen.getByRole("button", { name: /upload/i }));
  return user;
}

describe("the list", () => {
  it("shows the user's Contracts, each linking to its page", async () => {
    stubApi({ initial: [RENT] });
    render(<ContractsScreen />);
    const link = await screen.findByRole("link", { name: /residential rent agreement/i });
    expect(link).toHaveAttribute("href", "/contracts/c1");
    expect(screen.getByText(/12 clauses/i)).toBeInTheDocument();
  });

  it("says so when there are none", async () => {
    stubApi({ initial: [] });
    render(<ContractsScreen />);
    expect(await screen.findByText(/no contracts yet/i)).toBeInTheDocument();
  });

  it("asks for the list with the session token", async () => {
    const fn = stubApi({ initial: [] });
    render(<ContractsScreen />);
    await screen.findByText(/no contracts yet/i);
    const [url, init] = fn.mock.calls[0];
    expect(url).toMatch(/\/contracts$/);
    expect(init.headers.Authorization).toBe("Bearer session-token");
  });

  it("explains a failed load", async () => {
    stubApi({ listStatus: 503 });
    render(<ContractsScreen />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/unavailable/i);
  });
});

describe("uploading", () => {
  it("shows the Stages in order, then the new Contract in the list", async () => {
    let push!: (t: string) => void;
    let close!: () => void;
    const body = new ReadableStream<Uint8Array>({
      start(c) {
        push = (t) => c.enqueue(enc.encode(t));
        close = () => c.close();
      },
    });
    stubApi({
      initial: [],
      afterUpload: [RENT],
      upload: () => ({ ok: true, status: 200, body }),
    });
    await pasteAndUpload();
    push(STAGES);
    const progress = await screen.findByRole("status", { name: /progress/i });
    await within(progress).findByText("Indexing the Clauses");
    const labels = within(progress)
      .getAllByRole("listitem")
      .map((li) => li.querySelector("span[lang]")?.textContent);
    expect(labels).toEqual([
      "Reading your file",
      "Checking that it is a Contract in English",
      "Finding the Clauses",
      "Indexing the Clauses",
    ]);
    push(frame("answer", { id: "c1", title: RENT.title, clause_count: 12 }));
    close();
    const open = await screen.findByRole("link", { name: /residential rent agreement/i });
    expect(open).toHaveAttribute("href", "/contracts/c1");
    expect(await screen.findByText(/12 clauses/i)).toBeInTheDocument();
    expect(screen.queryByRole("status", { name: /progress/i })).toBeNull();
  });

  it("sends pasted text as the `text` field", async () => {
    const fn = stubApi({
      upload: () => sse([STAGES, frame("answer", { id: "c1", title: "T", clause_count: 2 })]),
    });
    await pasteAndUpload("1. A\nx.\n2. B\ny.");
    await waitFor(() => expect(fn.mock.calls.some(([, i]) => i?.method === "POST")).toBe(true));
    const post = fn.mock.calls.find(([, i]) => i?.method === "POST")!;
    expect(post[0]).toMatch(/\/contracts\/stream$/);
    const body = post[1].body as FormData;
    expect(body.get("text")).toBe("1. A\nx.\n2. B\ny.");
    expect(body.get("file")).toBeNull();
    expect(post[1].headers.Authorization).toBe("Bearer session-token");
  });

  it("sends a chosen file as the `file` field", async () => {
    const fn = stubApi({
      upload: () => sse([STAGES, frame("answer", { id: "c1", title: "T", clause_count: 2 })]),
    });
    const user = userEvent.setup();
    render(<ContractsScreen />);
    const file = new File(["%PDF-1.4"], "rent.pdf", { type: "application/pdf" });
    await user.upload(screen.getByLabelText(/choose a file/i), file);
    expect(screen.getByText("rent.pdf")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /upload/i }));
    await waitFor(() => expect(fn.mock.calls.some(([, i]) => i?.method === "POST")).toBe(true));
    const body = fn.mock.calls.find(([, i]) => i?.method === "POST")![1].body as FormData;
    expect((body.get("file") as File).name).toBe("rent.pdf");
  });

  it("takes a file dropped on the box", async () => {
    stubApi({});
    render(<ContractsScreen />);
    const file = new File(["x"], "dropped.docx");
    fireEvent.drop(screen.getByTestId("drop-zone"), { dataTransfer: { files: [file] } });
    expect(screen.getByText("dropped.docx")).toBeInTheDocument();
  });

  it("will not upload with nothing chosen", async () => {
    stubApi({});
    const user = userEvent.setup();
    render(<ContractsScreen />);
    expect(screen.getByRole("button", { name: /upload/i })).toBeDisabled();
    await user.click(screen.getByRole("tab", { name: /paste text/i }));
    expect(screen.getByRole("button", { name: /upload/i })).toBeDisabled();
  });

  it.each([
    ["not_a_contract", "LegalLens only explains Contracts."],
    ["not_english", "Only English Contracts are supported."],
    ["too_long", "That is longer than 30 pages."],
  ])("shows the reason a %s upload was refused, with no Try again", async (reason, message) => {
    stubApi({
      initial: [],
      upload: () => sse([stage("reading", "Reading your file"), frame("refusal", { reason, message })]),
    });
    await pasteAndUpload();
    expect(await screen.findByRole("status", { name: /refused/i })).toHaveTextContent(message);
    expect(screen.queryByRole("button", { name: /try again/i })).toBeNull();
  });

  it("shows an error, the Stage that failed and Try again when the stream reports one", async () => {
    stubApi({
      upload: () =>
        sse([
          stage("reading", "Reading your file"),
          stage("contract_check", "Checking that it is a Contract in English"),
          frame("error", { stage: "contract_check", message: "x" }),
        ]),
    });
    await pasteAndUpload();
    expect(await screen.findByRole("alert")).toHaveTextContent(/unavailable/i);
    expect(screen.getByText(/failed/i, { selector: "[aria-hidden]" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });

  it.each([
    [401, /session has expired/i],
    [413, /too large/i],
    [429, /limit/i],
    [503, /unavailable/i],
  ])("explains a %s from the server", async (status, message) => {
    stubApi({ upload: () => ({ ok: false, status }) });
    await pasteAndUpload();
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
  });

  it("says so when the connection fails", async () => {
    stubApi({
      upload: () => {
        throw new TypeError("network");
      },
    });
    await pasteAndUpload();
    expect(await screen.findByRole("alert")).toHaveTextContent(/could not reach/i);
  });
});
