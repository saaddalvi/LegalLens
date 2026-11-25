"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { useEffect, useState } from "react";
import { API_URL } from "@/lib/api-url";
import type { ContractDetail, ConversationTurn } from "@/lib/contract-types";
import BriefView from "./contract-brief";
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

// The Contract brief, the most recent Contract conversation (saved Queries and answers, and the
// box for the next one), then the Contract's Clauses verbatim.
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

  if (state === null) return <p className="text-muted">Loading…</p>;
  if ("error" in state)
    return (
      <div role="alert" className="flex flex-col items-start gap-3 border-l-2 border-redtape pl-4">
        <p className="text-redtape">{state.error}</p>
        <Link href="/contracts" className="underline underline-offset-4">
          Back to your Contracts
        </Link>
      </div>
    );
  const { contract } = state;
  return (
    <article className="flex flex-col gap-8">
      <header className="flex flex-col gap-2">
        <Link href="/contracts" className="self-start text-sm text-muted underline underline-offset-4">
          Your Contracts
        </Link>
        <h1 className="condensed break-words text-3xl">{contract.title}</h1>
        <p className="text-sm text-muted">
          {contract.clause_count} {contract.clause_count === 1 ? "Clause" : "Clauses"}
        </p>
      </header>
      <DeleteContract
        contractId={contract.id}
        title={contract.title}
        returnTo={`/contracts/${contract.id}`}
        onDeleted={() => {
          noteDeleted({ id: contract.id, title: contract.title });
          router.push("/contracts");
        }}
      />
      {contract.brief && <BriefView brief={contract.brief} />}
      <ContractConversation contractId={contract.id} conversationId={state.conversationId} initial={state.turns} />
      <h2 className="condensed text-xl">The Contract, Clause by Clause</h2>
      <ol className="flex flex-col gap-6">
        {contract.clauses.map((c) => (
          <li key={c.number} className="flex flex-col gap-2 border-l-2 border-stamp pl-4">
            <h2 className="text-sm font-semibold">
              {c.number === "0" ? (
                "Recitals and parties"
              ) : (
                <>
                  Clause {c.number}
                  {c.heading && <span className="font-normal text-muted"> · {c.heading}</span>}
                </>
              )}
            </h2>
            <p lang="en" className="max-w-[68ch] whitespace-pre-line break-words font-serif text-lg leading-relaxed">
              {c.text}
            </p>
          </li>
        ))}
      </ol>
    </article>
  );
}
