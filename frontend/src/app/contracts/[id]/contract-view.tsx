"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { useEffect, useLayoutEffect, useState } from "react";
import { API_URL } from "@/lib/api-url";
import { contractFacts } from "@/lib/contract-facts";
import type { ContractDetail, ConversationTurn } from "@/lib/contract-types";
import ClauseJumps, { ClauseItem, jumpTo } from "../../clause-links";
import BriefView, { Section } from "./contract-brief";
import DeleteContract from "../delete-contract";
import { noteDeleted } from "../deleted-notice";
import ContractConversation from "./contract-conversation";

// turns are those of the conversation on screen: the Contract's most recent one, if it has any.
type State =
  | { contract: ContractDetail; conversationId?: string; turns: ConversationTurn[] }
  | { error: string }
  | null;

function failure(status: number | null): string {
  if (status === 404) return "We could not find that Contract. It may have been deleted.";
  if (status === 401) return "Your session has expired. Please sign in again.";
  if (status === null) return "We could not reach the LegalLens service. Check your connection and try again.";
  return "The service is unavailable right now. Please try again shortly.";
}

// Follows an in-page link by scrolling and moving focus. A modified click is left to the browser.
function jumpOnClick(e: React.MouseEvent, id: string) {
  const target = document.getElementById(id);
  if (!target || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  e.preventDefault();
  jumpTo(target);
}

// The parts of this Contract's page, in order, as links under its title.
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
    <nav aria-label="On this page" className="mt-2 border-y border-rule py-1">
      <ul className="flex flex-wrap gap-x-5">
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
    const before = document.title;
    const apply = () => {
      if (document.title !== name) document.title = name;
    };
    apply();
    const watch = new MutationObserver(apply);
    watch.observe(document.head, { childList: true, characterData: true, subtree: true });
    return () => {
      watch.disconnect();
      // The next page may have named the tab already; leave its name alone.
      if (document.title === name) document.title = before;
    };
  }, [name]);
}

// An index, the Contract brief, the most recent Contract conversation (saved Queries and
// answers, and the box for the next one), the Contract's Clauses verbatim, and then Delete.
export default function ContractView({ id }: { id: string }) {
  const { getToken } = useAuth();
  const router = useRouter();
  const [state, setState] = useState<State>(null);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      try {
        const token = await getToken();
        const get = (path: string) =>
          fetch(`${API_URL}${path}`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            signal: controller.signal,
          });
        const path = `/contracts/${encodeURIComponent(id)}`;
        const res = await get(path);
        if (controller.signal.aborted) return;
        if (!res.ok) return setState({ error: failure(res.status) });
        const contract = (await res.json()) as ContractDetail;
        const latest = contract.conversations?.[0];
        let turns: ConversationTurn[] = [];
        if (latest) {
          const saved = await get(`${path}/conversations/${encodeURIComponent(latest.id)}`);
          if (controller.signal.aborted) return;
          // A 404 here is not the Contract's, which has just loaded.
          if (!saved.ok) return setState({ error: failure(saved.status === 404 ? null : saved.status) });
          turns = (await saved.json()) as ConversationTurn[];
        }
        setState({ contract, conversationId: latest?.id, turns });
      } catch {
        if (!controller.signal.aborted) setState({ error: failure(null) });
      }
    })();
    return () => controller.abort();
  }, [id, getToken]);

  const title = state && "contract" in state ? state.contract.title : null;
  useTabTitle(title && `${title} | LegalLens`);

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
    <ClauseJumps key={contract.id} numbers={contract.clauses.map((c) => c.number)}>
      <article className="flex flex-col gap-12">
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
          <PageIndex brief={contract.brief} />
        </header>
        {contract.brief && <BriefView brief={contract.brief} />}
        <ContractConversation contractId={contract.id} conversationId={state.conversationId} initial={state.turns} />
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
