# 03: Conversation list, URLs, new and delete

**What to build:** Each Contract conversation has its own URL, `/contracts/[id]/conversations/[cid]` (see `../spec.md`, "Frontend routes" and "UI"). `/contracts/[id]` opens the most recent conversation, or the empty new-conversation state at `/contracts/[id]/conversations/new` when the Contract has none. "New conversation" also goes to that `/new` URL. The Contract page's index lists the conversations newest first, titled with their first Query, under a "New conversation" button, with a phone-width equivalent. When a new conversation gets its first answer, the client receives the `conversation` event and replaces the URL with the real id without reloading. A conversation can be deleted after confirming, like a Contract. After deleting the open one, the next most recent opens, or the empty state if none is left. The brief shows once, above the open conversation. Switching conversations mid-answer cancels it, as leaving the page does now.

**Use the `impeccable` skill for all UI work in this issue**, following `DESIGN.md` and `PRODUCT.md`.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Component test: the index lists conversations newest first with their titles, and marks the open one
- [ ] Component test: "New conversation" shows an empty conversation, and its first answer replaces the URL with the new id and adds it to the top of the list
- [ ] Component test: opening `/contracts/[id]` with conversations shows the most recent one, and with none shows the empty state
- [ ] Component test: deleting a conversation asks for confirmation, removes it from the list and opens the next most recent
- [ ] Component test: switching conversations while an answer streams aborts that request, and the answer doesn't appear in either conversation
- [ ] Component test: refreshing a conversation URL shows the same turns
- [ ] Checked at phone width (375px) and desktop, in light and dark
- [ ] Lint, typecheck and tests pass
