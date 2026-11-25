import { useId, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { BUTTON_CLASS } from "../../ask-box";
import { isModifiedClick } from "../../clause-links";
import ConfirmDelete from "../confirm-delete";
import { detectedLang } from "@/lib/ask-stream";
import type { ConversationRef } from "@/lib/contract-types";
import { conversationHref, NEW } from "./conversation-address";

// The Contract's conversations, newest first, under the way to start another. Narrower screens
// have no margin to hold the list, so there it is folded away until asked for.
export default function ConversationList({
  contractId,
  conversations,
  openId,
  onOpen,
  onDeleted,
}: {
  contractId: string;
  conversations: ConversationRef[];
  openId: string | undefined;
  onOpen: (conversationId: string) => void;
  onDeleted: (conversationId: string) => void;
}) {
  const [announcement, setAnnouncement] = useState("");
  const [unfolded, setUnfolded] = useState(false);
  const listId = useId();
  const rows = useRef(new Map<string, HTMLLIElement>());
  const startButton = useRef<HTMLAnchorElement>(null);

  // Focus moves to a neighbour if the reader is still on the deleted row.
  function deleted({ id, title }: ConversationRef) {
    const row = rows.current.get(id);
    const active = document.activeElement;
    const held = row !== undefined && (active === document.body || row.contains(active));
    const neighbour = row?.nextElementSibling ?? row?.previousElementSibling;
    flushSync(() => onDeleted(id));
    if (held) (neighbour?.querySelector("a") ?? startButton.current)?.focus();
    setAnnouncement(`Deleted the conversation “${title}”.`);
  }

  // A link, so it can be opened in a new tab; a plain click stays on this page.
  const link = (conversationId: string) => ({
    href: conversationHref(contractId, conversationId),
    "aria-current": conversationId === openId ? ("page" as const) : undefined,
    onClick: (e: React.MouseEvent) => {
      if (isModifiedClick(e)) return;
      e.preventDefault();
      // Folded before the page moves to the conversation, which sits below the list.
      flushSync(() => setUnfolded(false));
      onOpen(conversationId);
    },
  });
  return (
    <nav aria-label="Conversations" className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
        <a ref={startButton} {...link(NEW)} className={`${BUTTON_CLASS} inline-flex min-h-11 items-center`}>
          New conversation
        </a>
        {conversations.length > 0 && (
          <button
            type="button"
            aria-expanded={unfolded}
            aria-controls={listId}
            onClick={() => setUnfolded((u) => !u)}
            className="min-h-11 underline underline-offset-4 xl:hidden"
          >
            {unfolded ? "Hide conversations" : `Show conversations (${conversations.length})`}
          </button>
        )}
      </div>
      {conversations.length > 0 && (
        <ul id={listId} className={`flex-col border-t border-rule xl:flex xl:text-sm ${unfolded ? "flex" : "hidden"}`}>
          {conversations.map((c) => (
            <li
              key={c.id}
              ref={(row) => {
                if (!row) return;
                rows.current.set(c.id, row);
                return () => void rows.current.delete(c.id);
              }}
              className="flex flex-wrap items-start gap-x-3 border-b border-rule"
            >
              <a
                {...link(c.id)}
                lang={detectedLang(c.title)}
                className="flex min-h-11 min-w-0 flex-1 items-center py-2 underline decoration-rule underline-offset-4 wrap-anywhere hover:decoration-ink aria-[current]:font-semibold aria-[current]:decoration-ink aria-[current]:decoration-2"
              >
                {c.title}
              </a>
              <ConfirmDelete
                path={conversationHref(contractId, c.id)}
                label={`Delete conversation: ${c.title}`}
                question="Delete this conversation? Its questions and answers are deleted. This cannot be undone."
                thing="conversation"
                returnTo={conversationHref(contractId, c.id)}
                onDeleted={() => deleted(c)}
              />
            </li>
          ))}
        </ul>
      )}
      <p role="status" className="sr-only">
        {announcement}
      </p>
    </nav>
  );
}
