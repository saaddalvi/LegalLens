"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { useEffect, useLayoutEffect, useState } from "react";
import { flushSync } from "react-dom";
import { API_URL } from "@/lib/api-url";
import { contractFacts } from "@/lib/contract-facts";
import type { ContractDetail, ConversationRef } from "@/lib/contract-types";
import ClauseJumps, { ClauseItem } from "../../clause-links";
import BriefView, { Section } from "./contract-brief";
import DeleteContract from "../delete-contract";
import { noteDeleted } from "../deleted-notice";
import ContractConversation from "./contract-conversation";
import { NEW, useOpenConversation } from "./conversation-address";
import ConversationList from "./conversation-list";
import Sidebar, { MenuButton, useSidebar } from "./sidebar";
import { starterQuestions } from "./starter-questions";
import Tabs, { Panel, type Tab, type TabEntry } from "./tabs";

type State = { contract: ContractDetail } | { error: string } | null;

function failure(status: number | null): string {
  if (status === 404) return "We could not find that Contract. It may have been deleted.";
  if (status === 401) return "Your session has expired. Please sign in again.";
  if (status === null) return "We could not reach the LegalLens service. Check your connection and try again.";
  return "The service is unavailable right now. Please try again shortly.";
}

// Names the tab for as long as this page is on screen. The Contract's title is only known
// once it has loaded, so the route's metadata cannot say it; and Next writes that metadata
// again on a return to the page, so the name is put back when it does. A layout effect, so
// that leaving stops the watch before the next page's name can be overwritten.
function useTabTitle(name: string | null) {
  useLayoutEffect(() => {
    if (!name) return;
    // As `document.title` reads it back, with runs of spaces collapsed. Compared as given,
    // such a name would never match, and each write would set off the watch again.
    const shown = name.replace(/[\t\n\f\r ]+/g, " ").trim();
    const before = document.title;
    const apply = () => {
      if (document.title !== shown) document.title = shown;
    };
    apply();
    const watch = new MutationObserver(apply);
    watch.observe(document.head, { childList: true, characterData: true, subtree: true });
    return () => {
      watch.disconnect();
      // The next page may have named the tab already; leave its name alone.
      if (document.title === shown) document.title = before;
    };
  }, [name]);
}

// A Contract's page, filling the window: its conversations at the side, and one of three parts in
// front. The open Contract conversation, the Contract brief, or the Contract's Clauses verbatim
// with Delete after them. The address says which conversation is open.
export default function ContractView({ id }: { id: string }) {
  const { getToken } = useAuth();
  const router = useRouter();
  const [state, setState] = useState<State>(null);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      try {
        const token = await getToken();
        const res = await fetch(`${API_URL}/contracts/${encodeURIComponent(id)}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (!res.ok) return setState({ error: failure(res.status) });
        setState({ contract: (await res.json()) as ContractDetail });
      } catch {
        if (!controller.signal.aborted) setState({ error: failure(null) });
      }
    })();
    return () => controller.abort();
  }, [id, getToken]);

  const loaded = state && "contract" in state ? state.contract : null;
  useTabTitle(loaded && `${loaded.title} | LegalLens`);
  const conversation = useOpenConversation(id, loaded ? (loaded.conversations[0]?.id ?? null) : undefined);
  const [tab, setTab] = useState<Tab>("chat");
  // Another conversation, however it was reached, is shown in front.
  const [seen, setSeen] = useState(conversation);
  if (seen.key !== conversation.key) {
    setSeen(conversation);
    if (seen.id !== undefined) setTab("chat");
  }
  const menu = useSidebar();

  // The list is the Contract's, so what happens to a conversation is written to both.
  function relist(change: (list: ContractDetail["conversations"]) => ContractDetail["conversations"]) {
    setState((s) =>
      s && "contract" in s
        ? { contract: { ...s.contract, conversations: change(s.contract.conversations) } }
        : s,
    );
  }

  // A Query was answered and saved: its conversation is now the latest, and a new one has an id.
  function saved(ref: ConversationRef) {
    const now = new Date().toISOString();
    relist((list) => {
      const before = list.find((c) => c.id === ref.id);
      return [
        { created_at: now, ...before, ...ref, updated_at: now },
        ...list.filter((c) => c.id !== ref.id),
      ];
    });
    conversation.changeId(NEW, ref.id);
  }

  const unlist = (conversationId: string) => relist((list) => list.filter((c) => c.id !== conversationId));

  // Deleted: if it was the open one, the latest of those left takes its place.
  function deleted(conversationId: string) {
    unlist(conversationId);
    conversation.drop(conversationId);
  }

  // Found to be gone when asked in: the page stays, now on a new conversation, so the
  // question can be asked again.
  function gone(conversationId: string) {
    unlist(conversationId);
    conversation.changeId(conversationId, NEW);
  }

  function show(conversationId: string) {
    flushSync(() => {
      setTab("chat");
      menu.dismiss();
    });
    conversation.show(conversationId);
    document.getElementById("conversation")?.focus({ preventScroll: true });
  }

  // A Clause, or the link that led to it, may be on a part that is behind.
  function reveal(element: HTMLElement) {
    const part = element.closest<HTMLElement>("[data-panel]")?.dataset.panel as Tab | undefined;
    if (part) flushSync(() => setTab(part));
  }

  if (state === null)
    return (
      <main className="p-4">
        <p className="text-muted">Loading…</p>
      </main>
    );
  if ("error" in state)
    return (
      <main className="p-4">
        <div role="alert" className="mx-auto flex max-w-2xl flex-col items-start gap-3 border-l-2 border-redtape pl-4">
          <p className="text-redtape">{state.error}</p>
          <Link href="/contracts" className="inline-flex min-h-11 items-center underline underline-offset-4">
            Back to your Contracts
          </Link>
        </div>
      </main>
    );
  const { contract } = state;
  const flags = contract.brief?.flagged_clauses.length ?? 0;
  const tabs: TabEntry[] = [
    { id: "chat", label: "Chat" },
    ...(contract.brief ? [{ id: "brief" as const, label: "Brief" }] : []),
    { id: "contract", label: "Contract" },
  ];

  function readBrief() {
    flushSync(() => setTab("brief"));
    document.getElementById("tab-brief")?.focus();
  }

  return (
    <ClauseJumps
      key={contract.id}
      numbers={contract.clauses.map((c) => c.number)}
      view={conversation.key}
      onReveal={reveal}
    >
      <div className="flex min-h-0 flex-1">
        <Sidebar menu={menu}>
          <ConversationList
            contractId={contract.id}
            conversations={contract.conversations}
            openId={conversation.id}
            onOpen={show}
            onDeleted={deleted}
          />
        </Sidebar>
        <main inert={menu.open} className="flex min-w-0 flex-1 flex-col">
          <div className="flex shrink-0 flex-wrap items-center gap-x-4 border-b border-rule px-4">
            <div className="flex min-w-0 flex-1 basis-full items-center gap-2 sm:basis-0">
              <MenuButton menu={menu} count={contract.conversations.length} />
              <h1 title={contract.title} className="condensed min-w-0 truncate py-2 text-xl">
                {contract.title}
              </h1>
            </div>
            <Tabs tabs={tabs} current={tab} onChoose={setTab} />
          </div>
          {/* The parts are stacked, so each keeps its place while another is in front. */}
          <div className="relative min-h-0 flex-1">
            <Panel id="chat" current={tab} className="flex flex-col">
              <h2 id="conversation" tabIndex={-1} className="sr-only">
                Ask about this Contract
              </h2>
              {conversation.id && (
                <ContractConversation
                  key={conversation.key}
                  contractId={contract.id}
                  conversationId={conversation.id === NEW ? undefined : conversation.id}
                  starters={starterQuestions(contract)}
                  flaggedCount={flags}
                  onReadBrief={contract.brief ? readBrief : undefined}
                  onSaved={saved}
                  onMissing={unlist}
                  onGone={gone}
                  onStartNew={() => show(NEW)}
                />
              )}
            </Panel>
            {contract.brief && (
              <Panel id="brief" current={tab} className="scroll-area">
                <div className="mx-auto w-full max-w-2xl px-4 py-6">
                  <BriefView brief={contract.brief} />
                </div>
              </Panel>
            )}
            <Panel id="contract" current={tab} className="scroll-area">
              <div className="mx-auto flex w-full max-w-2xl flex-col gap-8 px-4 py-6">
                <p className="text-sm text-muted">{contractFacts(contract)}</p>
                <Section id="contract-text" title="The Contract, Clause by Clause">
                  <ol data-clause-list className="flex flex-col gap-4">
                    {contract.clauses.map((c) => (
                      <ClauseItem key={c.number} number={c.number} heading={c.heading} text={c.text} />
                    ))}
                  </ol>
                </Section>
                <div className="border-t border-rule pt-4">
                  <DeleteContract
                    contractId={contract.id}
                    title={contract.title}
                    returnTo={`/contracts/${contract.id}`}
                    onDeleted={() => {
                      noteDeleted({ id: contract.id, title: contract.title });
                      router.push("/contracts");
                    }}
                  />
                </div>
              </div>
            </Panel>
          </div>
        </main>
      </div>
    </ClauseJumps>
  );
}
