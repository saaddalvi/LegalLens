import { useRef, useState } from "react";
import { flushSync } from "react-dom";
import { isModifiedClick } from "../../clause-links";
import ConfirmDelete from "../confirm-delete";
import { detectedLang } from "@/lib/ask-stream";
import type { ConversationRef } from "@/lib/contract-types";
import { conversationHref, NEW } from "./conversation-address";

// The Contract's conversations, newest first, under the way to start another.
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
      onOpen(conversationId);
    },
  });
  return (
    <nav aria-label="Conversations" className="flex min-h-0 flex-1 flex-col gap-3">
      <a
        ref={startButton}
        {...link(NEW)}
        className="mx-3 flex min-h-11 shrink-0 items-center gap-2 rounded-full border border-ink bg-paper px-4 font-semibold hover:bg-ink hover:text-ink-contrast"
      >
        <svg aria-hidden="true" viewBox="0 0 16 16" className="size-4 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.75">
          <path d="M8 3v10M3 8h10" strokeLinecap="round" />
        </svg>
        New conversation
      </a>
      {conversations.length > 0 && (
        // The padding keeps focus rings from being clipped by the scrolling box.
        <ul className="scroll-area flex min-h-0 flex-1 flex-col gap-0.5 px-3 py-1.5 text-sm">
          {conversations.map((c) => (
            <li
              key={c.id}
              ref={(row) => {
                if (!row) return;
                rows.current.set(c.id, row);
                return () => void rows.current.delete(c.id);
              }}
              className="group flex shrink-0 flex-wrap items-center rounded-lg hover:bg-paper/60 has-[a[aria-current]]:bg-paper"
            >
              <a
                {...link(c.id)}
                lang={detectedLang(c.title)}
                title={c.title}
                className="flex min-h-11 min-w-0 flex-1 items-center rounded-lg px-3 py-2 aria-[current]:font-semibold"
              >
                <span className="line-clamp-2 wrap-anywhere">{c.title}</span>
              </a>
              <ConfirmDelete
                path={conversationHref(contractId, c.id)}
                label={`Delete conversation: ${c.title}`}
                question="Delete this conversation? Its questions and answers are deleted. This cannot be undone."
                thing="conversation"
                returnTo={conversationHref(contractId, c.id)}
                onDeleted={() => deleted(c)}
                // On a pointer it waits for the row to be pointed at or focused.
                icon={
                  <svg aria-hidden="true" viewBox="0 0 16 16" className="size-4" fill="none" stroke="currentColor" strokeWidth="1.4">
                    <path d="M2.5 4h11M6 4V2.5h4V4M4 4l.7 9.5h6.6L12 4M6.6 6.5v4.5M9.4 6.5v4.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                }
                triggerClassName="inline-flex size-11 shrink-0 items-center justify-center rounded-lg text-muted hover:text-ink mouse:opacity-0 mouse:group-focus-within:opacity-100 mouse:group-hover:opacity-100"
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
