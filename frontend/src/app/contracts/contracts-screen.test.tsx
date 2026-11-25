import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ContractsScreen from "./contracts-screen";
import { noteDeleted } from "./deleted-notice";

const getToken = vi.fn();
let isSignedIn = true;
vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ getToken, isSignedIn }),
  SignInButton: ({ children }: { children: React.ReactNode }) => children,
}));

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

beforeEach(() => {
  getToken.mockReset().mockResolvedValue("session-token");
  isSignedIn = true;
});
afterEach(() => vi.unstubAllGlobals());

async function pasteAndUpload(text = "1. Term\nEleven months.\n2. Rent\nRs. 5.") {
  const user = userEvent.setup();
  render(<ContractsScreen />);
  await user.click(screen.getByRole("radio", { name: /paste text/i }));
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
  it("says before the upload what comes back, what is kept and what Google receives", () => {
    stubApi({});
    render(<ContractsScreen />);
    const terms = screen.getAllByRole("term").map((el) => el.textContent);
    expect(terms).toEqual(["You get", "LegalLens keeps", "Google receives"]);
    const [get, keeps, google] = screen.getAllByRole("definition");
    expect(get).toHaveTextContent(/won't tell you whether to sign/i);
    expect(keeps).toHaveTextContent(/until you delete the contract\. your file is not kept/i);
    expect(google).toHaveTextContent(/human reviewers may read them/i);
  });

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

  it("says what is missing and goes to it, sending nothing, when nothing is chosen", async () => {
    const fn = stubApi({});
    const user = userEvent.setup();
    render(<ContractsScreen />);
    await user.click(screen.getByRole("button", { name: "Upload" }));
    expect(screen.getByText("Choose a file first.")).toBeInTheDocument();
    expect(screen.getByLabelText(/choose a file/i)).toHaveFocus();
    await user.click(screen.getByRole("radio", { name: /paste text/i }));
    await user.click(screen.getByRole("button", { name: "Upload" }));
    expect(screen.getByText("Paste the Contract first.")).toBeInTheDocument();
    expect(screen.getByLabelText(/paste the contract/i)).toHaveFocus();
    expect(fn.mock.calls.some(([, i]) => i?.method === "POST")).toBe(false);
  });

  it("switches between a file and pasted text with the arrow keys", async () => {
    stubApi({});
    const user = userEvent.setup();
    render(<ContractsScreen />);
    screen.getByRole("radio", { name: /upload a file/i }).focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("radio", { name: /paste text/i })).toBeChecked();
    expect(screen.getByLabelText(/paste the contract/i)).toBeInTheDocument();
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
    expect(await screen.findByRole("region", { name: /refused/i })).toHaveTextContent(message);
    expect(announced()).toContain(message);
    expect(screen.getByRole("button", { name: "Upload" })).toHaveFocus();
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
    [413, /too large/i],
    [429, /too many/i],
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

describe("deleting", () => {
  const OTHER = { ...RENT, id: "c2", title: "Job offer" };

  function stubWithDelete(deleteResponse: unknown = { ok: true, status: 204 }) {
    const fn = vi.fn().mockImplementation(async (_url: string, init?: RequestInit) => {
      if (init?.method === "DELETE") return deleteResponse;
      return { ok: true, status: 200, json: async () => [RENT, OTHER] };
    });
    vi.stubGlobal("fetch", fn);
    return fn;
  }
  const deleteCalls = (fn: ReturnType<typeof vi.fn>) =>
    fn.mock.calls.filter(([, init]) => init?.method === "DELETE");

  it("asks for confirmation first, and cancelling deletes nothing", async () => {
    const fn = stubWithDelete();
    const user = userEvent.setup();
    render(<ContractsScreen />);
    await screen.findByRole("link", { name: /job offer/i });
    await user.click(screen.getByRole("button", { name: /delete job offer/i }));
    expect(screen.getByText(/delete this contract\?/i)).toBeInTheDocument();
    expect(deleteCalls(fn)).toHaveLength(0);
    await user.click(screen.getByRole("button", { name: /cancel/i }));
    expect(screen.queryByText(/delete this contract\?/i)).toBeNull();
    expect(deleteCalls(fn)).toHaveLength(0);
    expect(screen.getByRole("link", { name: /job offer/i })).toBeInTheDocument();
  });

  it("confirming deletes it on the server and removes it from the list", async () => {
    const fn = stubWithDelete();
    const user = userEvent.setup();
    render(<ContractsScreen />);
    await screen.findByRole("link", { name: /job offer/i });
    await user.click(screen.getByRole("button", { name: /delete job offer/i }));
    await user.click(screen.getByRole("button", { name: /yes, delete/i }));
    await waitFor(() => expect(screen.queryByRole("link", { name: /job offer/i })).toBeNull());
    expect(screen.getByRole("link", { name: /residential rent agreement/i })).toBeInTheDocument();
    const [[url, init]] = deleteCalls(fn);
    expect(url).toMatch(/\/contracts\/c2$/);
    expect(init.headers.Authorization).toBe("Bearer session-token");
  });

  it("keeps the Contract and says so when the delete fails", async () => {
    stubWithDelete({ ok: false, status: 503 });
    const user = userEvent.setup();
    render(<ContractsScreen />);
    await screen.findByRole("link", { name: /job offer/i });
    await user.click(screen.getByRole("button", { name: /delete job offer/i }));
    await user.click(screen.getByRole("button", { name: /yes, delete/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/could not delete/i);
    expect(screen.getByRole("link", { name: /job offer/i })).toBeInTheDocument();
  });
});

// What the screen-reader-only live region is saying.
const announced = () =>
  screen
    .getAllByRole("status")
    .filter((el) => el.classList.contains("sr-only"))
    .map((el) => el.textContent)
    .join(" ");

// An upload carries on after its screen is gone, so any left open is ended after each test.
const stillOpen: (() => void)[] = [];
afterEach(async () => {
  await act(async () => stillOpen.splice(0).forEach((end) => end()));
});

// An upload that stays open until the test pushes its frames.
function openUpload() {
  let push!: (t: string) => void;
  let close!: () => void;
  const body = new ReadableStream<Uint8Array>({
    start(c) {
      push = (t) => c.enqueue(enc.encode(t));
      let closed = false;
      close = () => {
        if (!closed) c.close();
        closed = true;
      };
      stillOpen.push(() => {
        try {
          close();
        } catch {
          // already cancelled by the reader
        }
      });
    },
  });
  return { upload: () => ({ ok: true, status: 200, body }), push, close };
}

const answer = frame("answer", { id: "c1", title: RENT.title, clause_count: 12 });
const posts = (fn: ReturnType<typeof vi.fn>) => fn.mock.calls.filter(([, i]) => i?.method === "POST");

// Whether closing the tab now would make the browser ask first.
function warnsOnLeave() {
  const e = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(e);
  return e.defaultPrevented;
}

describe("a finished upload", () => {
  it("focuses and announces a ready block with a link to the brief", async () => {
    stubApi({ upload: () => sse([STAGES, answer]) });
    await pasteAndUpload();
    const ready = await screen.findByRole("region", { name: "Your Contract brief is ready" });
    expect(ready).toHaveFocus();
    expect(ready).toHaveTextContent(RENT.title);
    expect(within(ready).getByRole("link", { name: /read the contract brief/i })).toHaveAttribute(
      "href",
      "/contracts/c1",
    );
    expect(announced()).toContain("Your Contract brief is ready");
  });

  it("clears the pasted text, so pressing Upload again sends nothing", async () => {
    const fn = stubApi({ upload: () => sse([STAGES, answer]) });
    const user = await pasteAndUpload();
    await screen.findByRole("region", { name: /brief is ready/i });
    expect(screen.getByLabelText(/paste the contract/i)).toHaveValue("");
    await user.click(screen.getByRole("button", { name: "Upload" }));
    expect(posts(fn)).toHaveLength(1);
  });

  it("clears the chosen file, and the same file can be chosen again", async () => {
    stubApi({ upload: () => sse([STAGES, answer]) });
    const user = userEvent.setup();
    render(<ContractsScreen />);
    const input = screen.getByLabelText(/choose a file/i) as HTMLInputElement;
    const file = new File(["%PDF-1.4"], "rent.pdf", { type: "application/pdf" });
    await user.upload(input, file);
    await user.click(screen.getByRole("button", { name: "Upload" }));
    await screen.findByRole("region", { name: /brief is ready/i });
    expect(screen.queryByText("rent.pdf")).toBeNull();
    expect(input.value).toBe("");
    await user.upload(input, file);
    expect(screen.getByText("rent.pdf")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: /brief is ready/i })).toBeNull();
  });

  it("drops the ready block when that Contract is deleted", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(async (_url: string, init?: RequestInit) => {
        if (init?.method === "POST") return sse([STAGES, answer]);
        if (init?.method === "DELETE") return { ok: true, status: 204 };
        return { ok: true, status: 200, json: async () => [RENT] };
      }),
    );
    const user = await pasteAndUpload();
    await screen.findByRole("region", { name: /brief is ready/i });
    await user.click(screen.getByRole("button", { name: /delete residential/i }));
    await user.click(screen.getByRole("button", { name: /yes, delete/i }));
    await waitFor(() => expect(screen.queryByRole("region", { name: /brief is ready/i })).toBeNull());
  });
});

describe("while uploading", () => {
  async function startUpload(text = "1. A") {
    const open = openUpload();
    const fn = stubApi({ upload: open.upload });
    const user = userEvent.setup();
    const view = render(<ContractsScreen />);
    await user.click(screen.getByRole("radio", { name: /paste text/i }));
    await user.type(screen.getByLabelText(/paste the contract/i), text);
    await user.click(screen.getByRole("button", { name: "Upload" }));
    await waitFor(() => expect(posts(fn)).toHaveLength(1));
    return { ...open, fn, user, view };
  }

  it("keeps focus on the button and ignores a second press", async () => {
    const { fn, user } = await startUpload();
    const button = screen.getByRole("button", { name: /working/i });
    expect(button).toHaveFocus();
    expect(button).toHaveAttribute("aria-disabled", "true");
    expect(button).toBeEnabled();
    await user.click(button);
    expect(posts(fn)).toHaveLength(1);
  });

  it("holds the file and text still", async () => {
    const { user } = await startUpload();
    expect(screen.getByLabelText(/paste the contract/i)).toHaveAttribute("readonly");
    await user.click(screen.getByRole("radio", { name: /upload a file/i }));
    fireEvent.drop(screen.getByTestId("drop-zone"), {
      dataTransfer: { files: [new File(["x"], "late.pdf")] },
    });
    expect(screen.queryByText("late.pdf")).toBeNull();
  });

  it("can be cancelled, which stops the request and returns to the button", async () => {
    const { fn, user, push } = await startUpload();
    await user.click(screen.getByRole("button", { name: /cancel upload/i }));
    expect(posts(fn)[0][1].signal.aborted).toBe(true);
    expect(screen.getByText(/upload cancelled.*may still count/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Upload" })).toHaveFocus();
    expect(screen.getByLabelText(/paste the contract/i)).toHaveValue("1. A");
    expect(screen.queryByRole("button", { name: /cancel upload/i })).toBeNull();
    await act(async () => push(answer)); // a late frame changes nothing
    expect(screen.queryByRole("region", { name: /brief is ready/i })).toBeNull();
    expect(warnsOnLeave()).toBe(false);
  });

  it("warns before the tab is closed, only until the upload ends", async () => {
    const { push, close } = await startUpload();
    expect(screen.getByText(/keep this tab open/i)).toBeInTheDocument();
    expect(warnsOnLeave()).toBe(true);
    push(answer);
    close();
    await screen.findByRole("region", { name: /brief is ready/i });
    expect(warnsOnLeave()).toBe(false);
    expect(screen.queryByText(/keep this tab open/i)).toBeNull();
  });

  it("carries on when the user moves to another page in the app", async () => {
    const { fn, view, push, close } = await startUpload();
    view.unmount();
    expect(posts(fn)[0][1].signal.aborted).toBe(false);
    expect(warnsOnLeave()).toBe(true);
    push(answer);
    close();
    await waitFor(() => expect(warnsOnLeave()).toBe(false));
  });
});

describe("the daily cap", () => {
  const capped = () => ({
    ok: false,
    status: 429,
    headers: new Headers({ "Retry-After": "19800", "X-Limit-Scope": "daily" }),
  });

  it("says when the limit resets and offers no Try again", async () => {
    stubApi({ upload: capped });
    await pasteAndUpload();
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/limit of new contracts for today/i);
    expect(alert).toHaveTextContent(/5 hours 30 minutes/i);
    expect(screen.queryByRole("button", { name: /try again/i })).toBeNull();
    expect(within(alert).getByRole("link", { name: /ask a question instead/i })).toHaveAttribute(
      "href",
      "/ask",
    );
  });

  it("leads to the Contracts already there", async () => {
    stubApi({ initial: [RENT], upload: capped });
    const user = await pasteAndUpload();
    await user.click(await screen.findByRole("button", { name: /go to your contracts/i }));
    expect(screen.getByRole("heading", { name: "Your Contracts" })).toHaveFocus();
  });
});

describe("the file picker", () => {
  const pdf = (name = "rent.pdf") => new File(["%PDF"], name, { type: "application/pdf" });
  const big = () => {
    const file = pdf("big.pdf");
    Object.defineProperty(file, "size", { value: 21 * 1024 * 1024 });
    return file;
  };
  const drop = (file: File) =>
    fireEvent.drop(screen.getByTestId("drop-zone"), { dataTransfer: { files: [file] } });
  const input = () => screen.getByLabelText(/choose (a|another) file/i) as HTMLInputElement;
  const uploadButton = () => screen.getByRole("button", { name: "Upload" });

  it("dims Upload, without removing it from the tab order, until there is a file", async () => {
    stubApi({});
    const user = userEvent.setup();
    render(<ContractsScreen />);
    expect(uploadButton()).toHaveAttribute("aria-disabled", "true");
    expect(uploadButton()).toBeEnabled();
    await user.upload(input(), pdf());
    expect(uploadButton()).not.toHaveAttribute("aria-disabled");
    await user.click(screen.getByRole("radio", { name: /paste text/i }));
    expect(uploadButton()).not.toHaveAttribute("aria-disabled");
  });

  it("removes the chosen file, so the same one can be chosen again", async () => {
    const fn = stubApi({});
    const user = userEvent.setup();
    render(<ContractsScreen />);
    expect(screen.queryByRole("button", { name: "Remove" })).toBeNull();
    await user.upload(input(), pdf());
    const remove = screen.getByRole("button", { name: "Remove" });
    expect(remove).toHaveAccessibleDescription("rent.pdf");
    await user.click(remove);
    expect(screen.queryByText("rent.pdf")).toBeNull();
    expect(input()).toHaveFocus();
    expect(input().value).toBe("");
    expect(announced()).toContain("Removed rent.pdf.");
    await user.click(uploadButton());
    expect(posts(fn)).toHaveLength(0);
    await user.upload(input(), pdf());
    expect(screen.getByText("rent.pdf")).toBeInTheDocument();
  });

  it.each([
    ["a file of another type", () => new File(["x"], "scan.jpg", { type: "image/jpeg" }), "scan.jpg is not a PDF or DOCX file."],
    ["an old Word file", () => new File(["x"], "old.doc", { type: "application/msword" }), "old.doc is not a PDF or DOCX file."],
    ["an empty file", () => new File([], "blank.pdf", { type: "application/pdf" }), "blank.pdf is empty."],
    ["a file over the limit", big, "That file is 21 MB. The limit is 20 MB."],
  ])("turns away %s as soon as it is dropped, and sends nothing", async (_name, make, message) => {
    const fn = stubApi({});
    const user = userEvent.setup();
    render(<ContractsScreen />);
    drop(make());
    expect(screen.getByRole("alert")).toHaveTextContent(message);
    expect(input()).toHaveAttribute("aria-invalid", "true");
    expect(input()).toHaveAccessibleDescription(message);
    expect(screen.queryByRole("button", { name: "Remove" })).toBeNull();
    expect(screen.queryByRole("button", { name: /try again/i })).toBeNull();
    await user.click(uploadButton());
    expect(posts(fn)).toHaveLength(0);
  });

  it("checks a file picked in the dialog, replacing the one already chosen", async () => {
    stubApi({});
    const user = userEvent.setup();
    render(<ContractsScreen />);
    await user.upload(input(), pdf());
    await user.upload(input(), big());
    expect(screen.getByRole("alert")).toHaveTextContent(/limit is 20 mb/i);
    expect(screen.queryByText("rent.pdf")).toBeNull();
    expect(screen.queryByText("big.pdf")).toBeNull();
  });

  it.each([
    ["only the name", new File(["%PDF"], "RENT.PDF")],
    ["only the type", new File(["%PDF"], "document", { type: "application/pdf" })],
  ])("accepts a file that says it is a PDF by %s", async (_name, file) => {
    stubApi({});
    render(<ContractsScreen />);
    await screen.findByText(/no contracts yet/i);
    drop(file);
    expect(screen.getByText(file.name)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("clears the message when another file is chosen", async () => {
    stubApi({});
    const user = userEvent.setup();
    render(<ContractsScreen />);
    await user.upload(input(), big());
    await user.upload(input(), pdf("small.pdf"));
    expect(screen.queryByRole("alert")).toBeNull();
    expect(input()).not.toHaveAttribute("aria-invalid");
  });

  it("offers pasting the text instead", async () => {
    stubApi({});
    const user = userEvent.setup();
    render(<ContractsScreen />);
    await user.upload(input(), big());
    await user.click(screen.getByRole("button", { name: /paste the text instead/i }));
    expect(screen.getByLabelText(/paste the contract/i)).toHaveFocus();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows the same message and actions when the server says it is too large", async () => {
    stubApi({ upload: () => ({ ok: false, status: 413 }) });
    const user = userEvent.setup();
    render(<ContractsScreen />);
    await user.upload(input(), pdf());
    await user.click(uploadButton());
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("That file is too large. The limit is 20 MB.");
    expect(screen.getByTestId("drop-zone")).toContainElement(alert);
    expect(screen.getByRole("button", { name: /paste the text instead/i })).toBeInTheDocument();
    expect(screen.queryByText("rent.pdf")).toBeNull();
    expect(screen.queryByRole("button", { name: /try again/i })).toBeNull();
  });
});

describe("an expired session", () => {
  const refused = () => ({ ok: false, status: 401 });
  const refusedDelete = () =>
    vi.fn().mockImplementation(async (_url: string, init?: RequestInit) =>
      init?.method === "DELETE"
        ? { ok: false, status: 401 }
        : { ok: true, status: 200, json: async () => [RENT] },
    );

  it("offers sign-in, not Try again, and keeps the text", async () => {
    isSignedIn = false;
    stubApi({ upload: refused });
    await pasteAndUpload("1. A");
    expect(await screen.findByRole("alert")).toHaveTextContent(/session has expired/i);
    expect(screen.getByRole("button", { name: /sign in again/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /try again/i })).toBeNull();
    expect(screen.getByLabelText(/paste the contract/i)).toHaveValue("1. A");
  });

  it("tries again with a fresh token while the browser still has a session", async () => {
    const fn = stubApi({ upload: refused });
    const user = await pasteAndUpload();
    await user.click(await screen.findByRole("button", { name: /try again/i }));
    await waitFor(() => expect(posts(fn)).toHaveLength(2));
    expect(getToken).toHaveBeenCalledWith({ skipCache: true });
  });

  it("offers sign-in when the list is refused", async () => {
    isSignedIn = false;
    stubApi({ listStatus: 401 });
    render(<ContractsScreen />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /session has expired.*see your contracts/i,
    );
    expect(screen.getByRole("button", { name: /sign in again/i })).toBeInTheDocument();
  });

  it("offers sign-in when a delete is refused", async () => {
    isSignedIn = false;
    vi.stubGlobal("fetch", refusedDelete());
    const user = userEvent.setup();
    render(<ContractsScreen />);
    await user.click(await screen.findByRole("button", { name: /delete residential/i }));
    await user.click(screen.getByRole("button", { name: /yes, delete/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/session has expired/i);
    expect(screen.getByRole("button", { name: /sign in again/i })).toBeInTheDocument();
  });
});

describe("a list that did not load", () => {
  it("can be loaded again", async () => {
    const fn = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 503 })
      .mockResolvedValue({ ok: true, status: 200, json: async () => [RENT] });
    vi.stubGlobal("fetch", fn);
    const user = userEvent.setup();
    render(<ContractsScreen />);
    await user.click(await screen.findByRole("button", { name: /try loading again/i }));
    expect(await screen.findByRole("link", { name: /residential/i })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.getByRole("heading", { name: "Your Contracts" })).toHaveFocus();
  });
});

describe("focus through a delete", () => {
  const OTHER = { ...RENT, id: "c2", title: "Job offer" };

  async function open(list: unknown[], del: () => unknown = () => ({ ok: true, status: 204 })) {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(async (_url: string, init?: RequestInit) =>
        init?.method === "DELETE" ? del() : { ok: true, status: 200, json: async () => list },
      ),
    );
    const user = userEvent.setup();
    render(<ContractsScreen />);
    await screen.findAllByRole("listitem");
    return user;
  }

  it("moves to Cancel, which reads out the question", async () => {
    const user = await open([RENT]);
    await user.click(screen.getByRole("button", { name: /delete residential/i }));
    const cancel = screen.getByRole("button", { name: "Cancel" });
    expect(cancel).toHaveFocus();
    expect(cancel).toHaveAccessibleDescription(/delete this contract\?/i);
  });

  it.each(["click", "escape"])("returns to Delete after %s", async (how) => {
    const user = await open([RENT]);
    await user.click(screen.getByRole("button", { name: /delete residential/i }));
    if (how === "click") await user.click(screen.getByRole("button", { name: "Cancel" }));
    else await user.keyboard("{Escape}");
    expect(screen.getByRole("button", { name: /delete residential/i })).toHaveFocus();
  });

  it("stays on the button while deleting", async () => {
    const user = await open([RENT], () => new Promise(() => {}));
    await user.click(screen.getByRole("button", { name: /delete residential/i }));
    await user.click(screen.getByRole("button", { name: /yes, delete/i }));
    const busy = screen.getByRole("button", { name: /deleting/i });
    expect(busy).toHaveFocus();
    expect(busy).toBeEnabled();
  });

  it.each([
    ["the next Contract", RENT.title, /^job offer$/i],
    ["the previous one when it was last", OTHER.title, /^residential rent agreement$/i],
  ])("moves to %s and announces the delete", async (_name, gone, neighbour) => {
    const user = await open([RENT, OTHER]);
    await user.click(screen.getByRole("button", { name: `Delete ${gone}` }));
    await user.click(screen.getByRole("button", { name: /yes, delete/i }));
    await waitFor(() => expect(screen.getByRole("link", { name: neighbour })).toHaveFocus());
    expect(announced()).toContain(`Deleted ${gone}.`);
  });

  it("moves to the list heading when none are left", async () => {
    const user = await open([RENT]);
    await user.click(screen.getByRole("button", { name: /delete residential/i }));
    await user.click(screen.getByRole("button", { name: /yes, delete/i }));
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Your Contracts" })).toHaveFocus(),
    );
  });

  it("announces a delete made on the Contract's own page", async () => {
    noteDeleted({ id: "c9", title: "Old lease" });
    stubApi({ initial: [RENT] });
    render(<ContractsScreen />);
    await waitFor(() => expect(announced()).toContain("Deleted Old lease."));
    expect(screen.getByRole("heading", { name: "Your Contracts" })).toHaveFocus();
  });
});
