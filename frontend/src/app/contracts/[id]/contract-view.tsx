"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { useEffect, useLayoutEffect, useState } from "react";
import { API_URL } from "@/lib/api-url";
import { contractFacts } from "@/lib/contract-facts";
import type { ContractDetail, ConversationRef } from "@/lib/contract-types";
import ClauseJumps, { ClauseItem, isModifiedClick, jumpTo } from "../../clause-links";
import BriefView, { Section } from "./contract-brief";
import DeleteContract from "../delete-contract";
import { noteDeleted } from "../deleted-notice";
import ContractConversation from "./contract-conversation";
import { NEW, useOpenConversation } from "./conversation-address";
import ConversationList from "./conversation-list";
import { starterQuestions } from "./starter-questions";

type State = { contract: ContractDetail } | { error: string } | null;

function failure(status: number | null): string {
  if (status === 404) return "We could not find that Contract. It may have been deleted.";
  if (status === 401) return "Your session has expired. Please sign in again.";
  if (status === null) return "We could not reach the LegalLens service. Check your connection and try again.";
  return "The service is unavailable right now. Please try again shortly.";
}

// Follows an in-page link by scrolling and moving focus. A modified click is left to the browser.
function jumpOnClick(e: React.MouseEvent, id: string) {
  const target = document.getElementById(id);
  if (!target || isModifiedClick(e)) return;
  e.preventDefault();
  jumpTo(target);
}

// The parts of this Contract's page, in order, as links.
function PageIndex({ brief }: { brief: ContractDetail["brief"] }) {
  const flags = brief?.flagged_clauses.length ?? 0;
  const entries = [
    brief && ["flagged", flags > 0 ? `Flagged clauses (${flags})` : "Flagged clauses"],
    brief && brief.key_terms.length > 0 && ["terms", "Key terms"],
    brief && brief.obligations.length > 0 && ["obligations", "What each party must do"],
    ["ask", "Ask about this Contract"],
    ["contract-text", "The Contract"],
  ].filter((e): e is string[] => Array.isArray(e));
  return (
    <nav aria-label="On this page" className="border-y border-rule py-1">
      <ul className="flex flex-wrap gap-x-5 xl:flex-col">
        {entries.map(([id, label]) => (
          <li key={id}>
            <a
              href={`#${id}`}
              onClick={(e) => jumpOnClick(e, id)}
              className="inline-flex min-h-11 items-center underline decoration-rule underline-offset-4 hover:decoration-ink"
            >
              {label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
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

// An index, the Contract brief, the open Contract conversation (saved Queries and answers, and
// the box for the next one), the Contract's Clauses verbatim, and then Delete. The index also
// lists the conversations; the address says which one is open.
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
    conversation.show(conversationId);
    const section = document.getElementById("ask");
    if (section) jumpTo(section);
  }

  if (state === null) return <p className="text-muted">Loading…</p>;
  if ("error" in state)
    return (
      <div role="alert" className="flex flex-col items-start gap-3 border-l-2 border-redtape pl-4">
        <p className="text-redtape">{state.error}</p>
        <Link href="/contracts" className="inline-flex min-h-11 items-center underline underline-offset-4">
          Back to your Contracts
        </Link>
      </div>
    );
  const { contract } = state;
  return (
    <ClauseJumps key={contract.id} numbers={contract.clauses.map((c) => c.number)} view={conversation.key}>
      <article className="relative flex flex-col gap-12">
        <header className="flex flex-col gap-2">
          <Link href="/contracts" className="inline-flex min-h-11 items-center self-start text-sm text-muted underline underline-offset-4 hover:text-ink">
            Your Contracts
          </Link>
          <h1 className="condensed break-words text-3xl">{contract.title}</h1>
          <p className="text-sm text-muted">{contractFacts(contract)}</p>
          <a
            href="#ask"
            lang="hi"
            onClick={(e) => jumpOnClick(e, "ask")}
            className="inline-flex min-h-11 items-center self-start underline decoration-rule underline-offset-4 hover:decoration-ink"
          >
            इस Contract के बारे में हिंदी में भी पूछ सकते हैं
          </a>
          {/* The page's index: under the title, or on wide screens in the empty margin left of
              the page column, where it stays in view as the page scrolls. */}
          <div className="mt-2 xl:absolute xl:inset-y-0 xl:right-full xl:mt-0 xl:mr-8 xl:w-56 2xl:mr-12 2xl:w-72">
            {/* The padding keeps focus rings from being clipped by the scrolling box. */}
            <div className="flex flex-col gap-4 xl:sticky xl:top-2 xl:-m-2 xl:max-h-[calc(100dvh-1rem-var(--dock-height,0px))] xl:overflow-y-auto xl:p-2">
              <PageIndex brief={contract.brief} />
              <ConversationList
                contractId={contract.id}
                conversations={contract.conversations}
                openId={conversation.id}
                onOpen={show}
                onDeleted={deleted}
              />
            </div>
          </div>
        </header>
        {contract.brief && <BriefView brief={contract.brief} />}
        <section id="ask" aria-labelledby="conversation" className="flex scroll-mt-4 flex-col gap-8">
          <h2 id="conversation" tabIndex={-1} data-jump-focus className="condensed self-start text-2xl">
            Ask about this Contract
          </h2>
          {conversation.id && (
            <ContractConversation
              key={conversation.key}
              contractId={contract.id}
              conversationId={conversation.id === NEW ? undefined : conversation.id}
              starters={starterQuestions(contract)}
              onSaved={saved}
              onMissing={unlist}
              onGone={gone}
              onStartNew={() => show(NEW)}
            />
          )}
        </section>
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
      </article>
    </ClauseJumps>
  );
}
