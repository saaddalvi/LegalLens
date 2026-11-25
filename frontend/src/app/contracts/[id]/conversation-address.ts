// Which Contract conversation a Contract's page shows is told by its address:
// /contracts/{id}/conversations/{cid}, where {cid} may be "new" for one not yet started.
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { flushSync } from "react-dom";
import { jumpState } from "../../clause-links";

export const NEW = "new";

// A conversation's address, here and under the API's own.
export const conversationHref = (contractId: string, conversationId: string) =>
  `/contracts/${encodeURIComponent(contractId)}/conversations/${encodeURIComponent(conversationId)}`;

const contractHref = (contractId: string) => `/contracts/${encodeURIComponent(contractId)}`;

// What an address says of this Contract: the conversation it names, null for the Contract
// itself, or undefined when it is some other page's.
function conversationIn(pathname: string, contractId: string): string | null | undefined {
  const [contracts, id, conversations, cid, more] = pathname.split("/").slice(1).map(decodeURIComponent);
  if (contracts !== "contracts" || id !== contractId || more) return undefined;
  if (!conversations) return null;
  return conversations === "conversations" && cid ? cid : undefined;
}

// Writes the history entry on show again under another address.
function readdress(href: string) {
  window.history.replaceState(jumpState(), "", href);
}

type Open = {
  id?: string;
  key: number;
  // The id the open conversation is about to be known by.
  becomes?: string;
  // What /new stands for since the new conversation was saved. Earlier history entries, such as
  // the one behind a Clause link, still have that address.
  savedAs?: string;
};

// The conversation to show: the one the address names, or else the most recent, or else a new
// one. `latest` is null for a Contract that has none, and undefined while that is unknown.
//
// `key` changes when another conversation is opened, so that nothing of the last one carries
// over. It stays when the open one only changes its id.
export function useOpenConversation(contractId: string, latest: string | null | undefined) {
  const named = conversationIn(usePathname(), contractId);
  const [open, setOpen] = useState<Open>({ key: 0 });
  // undefined while unknown, and while another page's address is showing: this one is then
  // kept hidden, and holds on to what it had.
  let shown: string | undefined;
  if (named === null) shown = latest === undefined ? undefined : (latest ?? NEW);
  else shown = named === NEW ? (open.savedAs ?? NEW) : named;
  if (shown !== undefined && shown !== open.id)
    setOpen({ id: shown, key: shown === open.becomes ? open.key : open.key + 1, savedAs: open.savedAs });

  // Moves an address that does not name the conversation on show to the one that does, keeping
  // any #clause.
  useEffect(() => {
    if (shown !== undefined && shown !== named)
      readdress(conversationHref(contractId, shown) + window.location.hash);
  }, [named, shown, contractId]);

  const isShowing = (conversationId: string) =>
    conversationIn(window.location.pathname, contractId) === conversationId;

  // Moving between conversations needs nothing from the server, so the browser's history is
  // written directly, which Next follows without loading anything.
  function show(conversationId: string) {
    if (conversationId === NEW) flushSync(() => setOpen((o) => ({ ...o, savedAs: undefined })));
    if (!isShowing(conversationId))
      window.history.pushState(null, "", conversationHref(contractId, conversationId));
    // Asked for again, a new conversation starts empty.
    else if (conversationId === NEW) setOpen((o) => ({ ...o, key: o.key + 1 }));
  }

  // The open conversation is now known by another id, and stays as it is: a new one was saved,
  // or a saved one was found to be gone and carries on as new. Nothing happens if the reader
  // has since opened another.
  function changeId(from: string, to: string) {
    if (!isShowing(from)) return;
    flushSync(() => setOpen((o) => ({ ...o, becomes: to, savedAs: from === NEW ? to : undefined })));
    readdress(conversationHref(contractId, to));
  }

  // A conversation was deleted. If it is the one on show, the page goes to the Contract's own
  // address, which leads to the latest of those left. The entry is written without any Clause
  // link's mark, as there is no way back to what was deleted.
  function drop(conversationId: string) {
    setOpen((o) => (o.savedAs === conversationId ? { ...o, savedAs: undefined } : o));
    if (isShowing(conversationId)) window.history.replaceState(null, "", contractHref(contractId));
  }

  return { id: open.id, key: open.key, show, changeId, drop };
}
