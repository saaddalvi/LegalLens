import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Activity } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import ContractView from "./contract-view";
import { visit } from "./fake-address";
import { ANSWER, controlled, type Conversation, fakeBackend, turn } from "./fake-backend";

vi.mock("next/navigation", async () => ({
  usePathname: (await import("./fake-address")).usePathname,
  useRouter: () => ({ push: vi.fn() }),
}));

const getToken = vi.fn(async () => "tok");
vi.mock("@clerk/nextjs", () => ({ useAuth: () => ({ getToken, isSignedIn: true }) }));

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
});
afterEach(() => vi.unstubAllGlobals());

const SAVED: Conversation[] = [
  { id: "newest", turns: [turn("What is the deposit?", "It is Rs. 1,00,000.")] },
  { id: "older", turns: [turn("Who repairs the flat?", "The landlord.")] },
];

const index = () => screen.getByRole("navigation", { name: "Conversations" });
const titles = () =>
  within(index())
    .queryAllByRole("listitem")
    .map((li) => within(li).getByRole("link").textContent);

async function open(path: string, saved = SAVED) {
  const backend = fakeBackend(saved);
  visit(path);
  const view = render(<ContractView id="c1" />);
  await screen.findByRole("heading", { name: "Rent agreement" });
  return { ...backend, ...view, user: userEvent.setup() };
}

it("lists the conversations newest first by title, and marks the open one", async () => {
  await open("/contracts/c1/conversations/older");
  expect(titles()).toEqual(["What is the deposit?", "Who repairs the flat?"]);
  const current = within(index()).getByRole("link", { current: "page" });
  expect(current).toHaveTextContent("Who repairs the flat?");
  expect(within(index()).getByRole("link", { name: "Who repairs the flat?" })).toHaveAttribute(
    "href",
    "/contracts/c1/conversations/older",
  );
  expect(within(index()).getByRole("link", { name: "New conversation" })).toHaveAttribute(
    "href",
    "/contracts/c1/conversations/new",
  );
  expect(await screen.findByText("The landlord.")).toBeInTheDocument();
});

const box = () => screen.findByLabelText(/ask a question about this contract/i);

async function ask(user: ReturnType<typeof userEvent.setup>, q: string) {
  await user.type(await box(), q);
  await user.click(screen.getByRole("button", { name: /^Ask( this instead)?$/ }));
}

it("shows an empty conversation for New conversation, whose first answer gives it an address and the top of the list", async () => {
  const { user, fetch } = await open("/contracts/c1/conversations/newest");
  await screen.findByText("It is Rs. 1,00,000.");
  const entries = window.history.length;

  await user.click(within(index()).getByRole("link", { name: "New conversation" }));
  expect(window.location.pathname).toBe("/contracts/c1/conversations/new");
  expect(screen.queryByText("It is Rs. 1,00,000.")).not.toBeInTheDocument();
  expect(within(index()).getByRole("link", { current: "page" })).toHaveTextContent("New conversation");
  expect(screen.getByText(/your first question starts a new conversation/i)).toBeInTheDocument();

  await ask(user, "Can I sublet?");
  expect(await screen.findByText("Answer to: Can I sublet?")).toBeInTheDocument();
  expect(window.location.pathname).toBe("/contracts/c1/conversations/new-1");
  expect(window.history.length).toBe(entries + 1); // replaced, not another entry
  expect(titles()).toEqual(["Can I sublet?", "What is the deposit?", "Who repairs the flat?"]);
  expect(within(index()).getByRole("link", { current: "page" })).toHaveTextContent("Can I sublet?");
  // The same conversation still: nothing was fetched for it, and the next Query goes into it.
  expect(fetch.mock.calls.some(([url]) => url.endsWith("/conversations/new-1"))).toBe(false);
  await ask(user, "For how long?");
  expect(await screen.findByText("Answer to: For how long?")).toBeInTheDocument();
  expect(screen.getByText("Answer to: Can I sublet?")).toBeInTheDocument();
  expect(JSON.parse(fetch.mock.lastCall![1]!.body as string).conversation_id).toBe("new-1");
});

it("moves a conversation to the top of the list when it is asked in again", async () => {
  const { user } = await open("/contracts/c1/conversations/older");
  await screen.findByText("The landlord.");
  await ask(user, "And the roof?");
  await screen.findByText("Answer to: And the roof?");
  expect(titles()).toEqual(["Who repairs the flat?", "What is the deposit?"]);
});

it("starts afresh on New conversation when already on one that has not been saved", async () => {
  const { user, hold } = await open("/contracts/c1/conversations/new");
  const slow = controlled();
  hold(slow.res);
  await ask(user, "Can I sublet?");
  await screen.findByText("Can I sublet?");
  await user.click(within(index()).getByRole("link", { name: "New conversation" }));
  expect(screen.queryByText("Can I sublet?")).not.toBeInTheDocument();
});

it("moves from a Contract's own address to its most recent conversation, without another history entry", async () => {
  const entries = window.history.length;
  await open("/contracts/c1");
  expect(await screen.findByText("It is Rs. 1,00,000.")).toBeInTheDocument();
  expect(screen.queryByText("The landlord.")).not.toBeInTheDocument();
  expect(window.location.pathname).toBe("/contracts/c1/conversations/newest");
  expect(window.history.length).toBe(entries);
});

it("moves from the address of a Contract with no conversations to an empty new one", async () => {
  const { fetch } = await open("/contracts/c1", []);
  expect(await box()).toBeInTheDocument();
  expect(screen.getByText(/your first question starts a new conversation/i)).toBeInTheDocument();
  expect(window.location.pathname).toBe("/contracts/c1/conversations/new");
  expect(titles()).toEqual([]);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("shows the same turns when a conversation's address is opened again", async () => {
  const first = await open("/contracts/c1/conversations/new", []);
  await ask(first.user, "Can I sublet?");
  await screen.findByText("Answer to: Can I sublet?");
  await ask(first.user, "For how long?");
  await screen.findByText("Answer to: For how long?");
  const address = window.location.pathname;
  const asked = () => screen.getAllByText("You asked:").map((e) => e.parentElement!.textContent);
  const before = asked();
  first.unmount();

  // A refresh: the page starts over from the address, against what was saved.
  visit(address);
  render(<ContractView id="c1" />);
  expect(await screen.findByText("Answer to: For how long?")).toBeInTheDocument();
  expect(screen.getByText("Answer to: Can I sublet?")).toBeInTheDocument();
  expect(asked()).toEqual(before);
  expect(window.location.pathname).toBe(address);
});

it("opens another conversation chosen from the index, and goes back with the browser", async () => {
  const { user } = await open("/contracts/c1/conversations/newest");
  await screen.findByText("It is Rs. 1,00,000.");
  await user.click(within(index()).getByRole("link", { name: "Who repairs the flat?" }));
  expect(await screen.findByText("The landlord.")).toBeInTheDocument();
  expect(screen.queryByText("It is Rs. 1,00,000.")).not.toBeInTheDocument();
  expect(window.location.pathname).toBe("/contracts/c1/conversations/older");
  expect(screen.getByRole("heading", { name: "Ask about this Contract" })).toHaveFocus();
  window.history.back();
  expect(await screen.findByText("It is Rs. 1,00,000.")).toBeInTheDocument();
  expect(screen.queryByText("The landlord.")).not.toBeInTheDocument();
});

it("cancels the answer being written when another conversation is opened, and shows it in neither", async () => {
  const { user, hold, fetch } = await open("/contracts/c1/conversations/newest");
  await screen.findByText("It is Rs. 1,00,000.");
  const slow = controlled();
  hold(slow.res);
  await ask(user, "Can I sublet?");
  slow.push("stage", { id: "scope_check", label: "Checking your question" });
  await screen.findByText("Checking your question");
  const signal = fetch.mock.lastCall![1]!.signal!;
  expect(signal.aborted).toBe(false);

  await user.click(within(index()).getByRole("link", { name: "Who repairs the flat?" }));
  expect(signal.aborted).toBe(true);
  await screen.findByText("The landlord.");
  // Whatever the cancelled stream still delivers is ignored.
  try {
    slow.push("conversation", { id: "newest", title: "What is the deposit?" });
    slow.push("answer", { ...ANSWER, answer: "STALE ANSWER" });
    slow.close();
  } catch {
    // The page has already closed the stream.
  }
  await new Promise((resolve) => setTimeout(resolve, 20));
  expect(screen.queryByText("STALE ANSWER")).not.toBeInTheDocument();
  expect(screen.queryByText("Can I sublet?")).not.toBeInTheDocument();
  expect(screen.queryByText("Checking your question")).not.toBeInTheDocument();
  expect(window.location.pathname).toBe("/contracts/c1/conversations/older");
  expect(titles()).toEqual(["What is the deposit?", "Who repairs the flat?"]);

  await user.click(within(index()).getByRole("link", { name: "What is the deposit?" }));
  expect(await screen.findByText("It is Rs. 1,00,000.")).toBeInTheDocument();
  expect(screen.queryByText("STALE ANSWER")).not.toBeInTheDocument();
  expect(screen.queryByText("Can I sublet?")).not.toBeInTheDocument();
});

it("cancels a new conversation's first answer when another is opened", async () => {
  const { user, hold, fetch } = await open("/contracts/c1/conversations/new");
  const slow = controlled();
  hold(slow.res);
  await ask(user, "Can I sublet?");
  const signal = fetch.mock.lastCall![1]!.signal!;
  await user.click(within(index()).getByRole("link", { name: "What is the deposit?" }));
  expect(signal.aborted).toBe(true);
  await screen.findByText("It is Rs. 1,00,000.");
  expect(window.location.pathname).toBe("/contracts/c1/conversations/newest");
  expect(titles()).toEqual(["What is the deposit?", "Who repairs the flat?"]);
});

const remove = (title: string) => within(index()).getByRole("button", { name: `Delete conversation: ${title}` });
const deletes = (fetch: ReturnType<typeof fakeBackend>["fetch"]) =>
  fetch.mock.calls.filter(([, init]) => init?.method === "DELETE");

it("asks before deleting the open conversation, then removes it and opens the next most recent", async () => {
  const { user, fetch } = await open("/contracts/c1/conversations/newest");
  await screen.findByText("It is Rs. 1,00,000.");
  const entries = window.history.length;

  await user.click(remove("What is the deposit?"));
  expect(screen.getByText(/delete this conversation\?/i)).toBeInTheDocument();
  expect(deletes(fetch)).toHaveLength(0);
  await user.click(screen.getByRole("button", { name: "Cancel" }));
  expect(remove("What is the deposit?")).toHaveFocus();

  await user.click(remove("What is the deposit?"));
  await user.click(screen.getByRole("button", { name: "Yes, delete" }));
  expect(await screen.findByText("The landlord.")).toBeInTheDocument();
  expect(screen.queryByText("It is Rs. 1,00,000.")).not.toBeInTheDocument();
  expect(titles()).toEqual(["Who repairs the flat?"]);
  expect(window.location.pathname).toBe("/contracts/c1/conversations/older");
  expect(window.history.length).toBe(entries); // Back does not return to what was deleted
  const [[url, init]] = deletes(fetch);
  expect(url).toMatch(/\/contracts\/c1\/conversations\/newest$/);
  expect((init!.headers as Record<string, string>).Authorization).toBe("Bearer tok");
  expect(within(index()).getByRole("link", { name: "Who repairs the flat?" })).toHaveFocus();
  expect(screen.getByText("Deleted the conversation “What is the deposit?”.")).toBeInTheDocument();
});

it("shows the empty state after the last conversation is deleted", async () => {
  const { user } = await open("/contracts/c1/conversations/newest", SAVED.slice(0, 1));
  await screen.findByText("It is Rs. 1,00,000.");
  await user.click(remove("What is the deposit?"));
  await user.click(screen.getByRole("button", { name: "Yes, delete" }));
  expect(await screen.findByText(/your first question starts a new conversation/i)).toBeInTheDocument();
  expect(window.location.pathname).toBe("/contracts/c1/conversations/new");
  expect(titles()).toEqual([]);
  expect(within(index()).getByRole("link", { name: "New conversation" })).toHaveFocus();
});

it("leaves the open conversation as it is when another is deleted", async () => {
  const { user, fetch } = await open("/contracts/c1/conversations/newest");
  await screen.findByText("It is Rs. 1,00,000.");
  await user.click(remove("Who repairs the flat?"));
  await user.click(screen.getByRole("button", { name: "Yes, delete" }));
  await waitFor(() => expect(titles()).toEqual(["What is the deposit?"]));
  expect(screen.getByText("It is Rs. 1,00,000.")).toBeInTheDocument();
  expect(window.location.pathname).toBe("/contracts/c1/conversations/newest");
  expect(fetch.mock.calls.filter(([url]) => url.endsWith("/conversations/newest"))).toHaveLength(1);
});

it("cancels the answer being written when its conversation is deleted", async () => {
  const { user, hold, fetch } = await open("/contracts/c1/conversations/newest");
  await screen.findByText("It is Rs. 1,00,000.");
  hold(controlled().res);
  await ask(user, "Can I sublet?");
  const signal = fetch.mock.lastCall![1]!.signal!;
  await user.click(remove("What is the deposit?"));
  await user.click(screen.getByRole("button", { name: "Yes, delete" }));
  await screen.findByText("The landlord.");
  expect(signal.aborted).toBe(true);
  expect(screen.queryByText("Can I sublet?")).not.toBeInTheDocument();
});

it("says a conversation's address leads nowhere, and offers a new one", async () => {
  const { user } = await open("/contracts/c1/conversations/gone");
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent(/could not find that conversation/i);
  expect(screen.queryByLabelText(/ask a question about this contract/i)).not.toBeInTheDocument();
  await user.click(within(alert).getByRole("button", { name: "Start a new conversation" }));
  expect(await box()).toBeInTheDocument();
  expect(window.location.pathname).toBe("/contracts/c1/conversations/new");
});

it("drops a conversation found to be gone when asked in, and keeps the question to try again", async () => {
  const { user, hold } = await open("/contracts/c1/conversations/newest");
  await screen.findByText("It is Rs. 1,00,000.");
  hold(new Response(null, { status: 404 }));
  await ask(user, "Can I sublet?");
  expect(await screen.findByRole("alert")).toHaveTextContent(/could not find that conversation/i);
  expect(titles()).toEqual(["Who repairs the flat?"]);
  expect(window.location.pathname).toBe("/contracts/c1/conversations/new");
  await user.click(screen.getByRole("button", { name: "Try again" }));
  expect(await screen.findByText("Answer to: Can I sublet?")).toBeInTheDocument();
  expect(window.location.pathname).toBe("/contracts/c1/conversations/new-1");
  expect(titles()).toEqual(["Can I sublet?", "Who repairs the flat?"]);
});

it("keeps a conversation saved during a Clause jump on screen on the way back", async () => {
  const { user, hold } = await open("/contracts/c1/conversations/new", []);
  const slow = controlled();
  hold(slow.res);
  await ask(user, "Can I sublet?");
  // While the answer is written, the reader follows a cross-reference to another Clause.
  await user.click(screen.getByRole("link", { name: "Clause 3" }));
  slow.push("conversation", { id: "new-1", title: "Can I sublet?" });
  slow.push("answer", ANSWER);
  slow.close();
  await screen.findByText(ANSWER.answer);
  window.history.back(); // the browser's own Back
  await waitFor(() => expect(screen.queryByRole("button", { name: /^Back to/ })).not.toBeInTheDocument());
  expect(window.location.pathname).toBe("/contracts/c1/conversations/new-1");
  expect(screen.getByText(ANSWER.answer)).toBeInTheDocument();
});

it("drops the way back from a Clause when another conversation is opened", async () => {
  const { user } = await open("/contracts/c1/conversations/newest");
  await screen.findByText("It is Rs. 1,00,000.");
  await user.click(screen.getByRole("link", { name: "Clause 3" }));
  expect(screen.getByRole("button", { name: /^Back to/ })).toBeInTheDocument();
  await user.click(within(index()).getByRole("link", { name: "Who repairs the flat?" }));
  expect(screen.queryByRole("button", { name: /^Back to/ })).not.toBeInTheDocument();
});

// Next keeps a page that has been left, hidden, and may show it again.
it("cancels the answer being written when the page is left, and shows no sign of it on return", async () => {
  const { fetch, hold } = fakeBackend(SAVED);
  visit("/contracts/c1/conversations/newest");
  const page = (mode: "visible" | "hidden") => (
    <Activity mode={mode}>
      <ContractView id="c1" />
    </Activity>
  );
  const { rerender } = render(page("visible"));
  const user = userEvent.setup();
  await screen.findByText("It is Rs. 1,00,000.");
  const slow = controlled();
  hold(slow.res);
  await ask(user, "Can I sublet?");
  slow.push("stage", { id: "scope_check", label: "Checking your question" });
  await screen.findByText("Checking your question");
  const signal = fetch.mock.lastCall![1]!.signal!;

  act(() => visit("/contracts")); // another page's address, which this one must not act on
  rerender(page("hidden"));
  expect(signal.aborted).toBe(true);
  act(() => visit("/contracts/c1/conversations/newest"));
  rerender(page("visible"));

  expect(await screen.findByText("It is Rs. 1,00,000.")).toBeInTheDocument();
  expect(screen.queryByText("Can I sublet?")).not.toBeInTheDocument();
  expect(screen.queryByText("Checking your question")).not.toBeInTheDocument();
  expect(window.location.pathname).toBe("/contracts/c1/conversations/newest");
});

// On screens too narrow to keep it beside the page.
it("opens the conversations as a drawer, and closes it once one is chosen", async () => {
  const { user } = await open("/contracts/c1/conversations/newest");
  const toggle = screen.getByRole("button", { name: "Show conversations (2)" });
  expect(toggle).toHaveAttribute("aria-expanded", "false");

  await user.click(toggle);
  expect(toggle).toHaveAttribute("aria-expanded", "true");
  expect(within(index()).getByRole("link", { name: "New conversation" })).toHaveFocus();
  expect(screen.getByRole("main")).toHaveAttribute("inert");

  await user.keyboard("{Escape}");
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  expect(toggle).toHaveFocus();
  expect(screen.getByRole("main")).not.toHaveAttribute("inert");

  await user.click(toggle);
  await user.click(within(index()).getByRole("link", { name: "Who repairs the flat?" }));
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  expect(screen.getByRole("heading", { name: "Ask about this Contract" })).toHaveFocus();
});

it("leaves the drawer open when Escape dismisses a delete confirmation", async () => {
  const { user } = await open("/contracts/c1/conversations/newest");
  const toggle = screen.getByRole("button", { name: "Show conversations (2)" });
  await user.click(toggle);
  await user.click(remove("What is the deposit?"));
  await user.keyboard("{Escape}");
  expect(screen.queryByText(/delete this conversation\?/i)).not.toBeInTheDocument();
  expect(toggle).toHaveAttribute("aria-expanded", "true");
});

it("starts empty on New conversation after one has just been saved", async () => {
  const { user } = await open("/contracts/c1/conversations/new", []);
  await ask(user, "Can I sublet?");
  await screen.findByText("Answer to: Can I sublet?");
  await user.click(within(index()).getByRole("link", { name: "New conversation" }));
  expect(screen.queryByText("Answer to: Can I sublet?")).not.toBeInTheDocument();
  expect(window.location.pathname).toBe("/contracts/c1/conversations/new");
  await ask(user, "For how long?");
  await screen.findByText("Answer to: For how long?");
  expect(window.location.pathname).toBe("/contracts/c1/conversations/new-2");
});

// Answers the matching requests with whatever the test says, and the rest as usual.
function intercept(
  fetch: ReturnType<typeof fakeBackend>["fetch"],
  matches: (url: string, init?: RequestInit) => boolean,
  respond: (usual: () => Promise<Response>) => Promise<Response>,
) {
  const usual = fetch.getMockImplementation()!;
  fetch.mockImplementation((url, init) =>
    matches(url, init) ? respond(() => usual(url, init)) : usual(url, init),
  );
}

it("opens one that is left when a second deletion finishes after the first", async () => {
  const third = { id: "oldest", turns: [turn("Can I paint?", "With consent.")] };
  const { user, fetch } = await open("/contracts/c1/conversations/newest", [...SAVED, third]);
  await screen.findByText("It is Rs. 1,00,000.");
  const release: (() => Promise<void>)[] = [];
  intercept(
    fetch,
    (_, init) => init?.method === "DELETE",
    (usual) => new Promise((resolve) => release.push(async () => resolve(await usual()))),
  );

  for (const title of ["Who repairs the flat?", "What is the deposit?"]) {
    await user.click(remove(title));
    const row = remove("Can I paint?").closest("ul")!;
    const buttons = within(row).getAllByRole("button", { name: /^(Yes, delete|Deleting…)$/ });
    await user.click(buttons.find((b) => b.textContent === "Yes, delete")!);
  }
  await act(() => release[0]()); // the one that is not open
  await act(() => release[1]()); // then the open one

  expect(await screen.findByText("With consent.")).toBeInTheDocument();
  expect(window.location.pathname).toBe("/contracts/c1/conversations/oldest");
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

it("does not lead back to a deleted conversation from a Clause", async () => {
  const { user } = await open("/contracts/c1/conversations/newest");
  await screen.findByText("It is Rs. 1,00,000.");
  await user.click(screen.getByRole("link", { name: "Clause 3" }));
  await user.click(remove("What is the deposit?"));
  await user.click(screen.getByRole("button", { name: "Yes, delete" }));
  await screen.findByText("The landlord.");
  await user.click(screen.getByRole("link", { name: "Clause 3" }));
  await user.click(screen.getByRole("button", { name: /^Back to/ }));
  await waitFor(() => expect(screen.queryByRole("button", { name: /^Back to/ })).not.toBeInTheDocument());
  expect(window.location.pathname).toBe("/contracts/c1/conversations/older");
  expect(screen.getByText("The landlord.")).toBeInTheDocument();
});

it("loads a conversation again on Try again", async () => {
  const backend = fakeBackend(SAVED);
  let failures = 1;
  intercept(
    backend.fetch,
    (url) => url.endsWith("/conversations/older"),
    async (usual) => (failures-- > 0 ? new Response(null, { status: 503 }) : usual()),
  );
  visit("/contracts/c1/conversations/older");
  render(<ContractView id="c1" />);
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent(/unavailable/i);
  await userEvent.click(within(alert).getByRole("button", { name: "Try again" }));
  expect(await screen.findByText("The landlord.")).toBeInTheDocument();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

it("takes a conversation that turns out to be gone off the list", async () => {
  const backend = fakeBackend(SAVED);
  // Deleted elsewhere, after the Contract was listed.
  intercept(
    backend.fetch,
    (url) => url.endsWith("/conversations/older"),
    async () => new Response(null, { status: 404 }),
  );
  visit("/contracts/c1/conversations/older");
  render(<ContractView id="c1" />);
  expect(await screen.findByRole("alert")).toHaveTextContent(/could not find that conversation/i);
  expect(titles()).toEqual(["What is the deposit?"]);
});
