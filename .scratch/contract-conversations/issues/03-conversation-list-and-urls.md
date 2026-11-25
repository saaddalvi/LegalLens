# 03: Conversation list, URLs, new and delete

**What to build:** Each Contract conversation has its own URL, `/contracts/[id]/conversations/[cid]` (see `../spec.md`, "Frontend routes" and "UI"). `/contracts/[id]` opens the most recent conversation, or the empty new-conversation state at `/contracts/[id]/conversations/new` when the Contract has none. "New conversation" also goes to that `/new` URL. The Contract page's index lists the conversations newest first, titled with their first Query, under a "New conversation" button, with a phone-width equivalent. When a new conversation gets its first answer, the client receives the `conversation` event and replaces the URL with the real id without reloading. A conversation can be deleted after confirming, like a Contract. After deleting the open one, the next most recent opens, or the empty state if none is left. The brief shows once, above the open conversation. Switching conversations mid-answer cancels it, as leaving the page does now.

**Use the `impeccable` skill for all UI work in this issue**, following `DESIGN.md` and `PRODUCT.md`.

**Blocked by:** 01

**Status:** done

- [x] Component test: the index lists conversations newest first with their titles, and marks the open one
- [x] Component test: "New conversation" shows an empty conversation, and its first answer replaces the URL with the new id and adds it to the top of the list
- [x] Component test: opening `/contracts/[id]` with conversations shows the most recent one, and with none shows the empty state
- [x] Component test: deleting a conversation asks for confirmation, removes it from the list and opens the next most recent
- [x] Component test: switching conversations while an answer streams aborts that request, and the answer doesn't appear in either conversation
- [x] Component test: refreshing a conversation URL shows the same turns
- [x] Checked at phone width (375px) and desktop, in light and dark
- [x] Lint, typecheck and tests pass

## Comments

2026-11-25: Implemented in commit 1b6dead. 248 frontend tests pass, typecheck and eslint are clean, and the production build succeeds. No backend code changed.

Checked in a browser at 320, 375, 900, 1280, 1440 and 1920px, light and dark, on a copy of the frontend with stubbed sign-in and a fake API. Not checked against real Clerk, the real backend or a real phone.

Choices the ticket left open:

- At 1280px and up the whole page index, "On this page" included, sits in the left margin, as the Contracts list does. Below that it stays under the title and the conversation list is folded behind "Show conversations (n)".
- After the open conversation is deleted, the most recent of those left opens.
- Once a new conversation is saved, an older history entry for `conversations/new` shows that conversation, until "New conversation" is chosen again. Without this, Back from a Clause link followed mid-answer would swap to an empty conversation.

The upload screen still says LegalLens keeps questions and answers "until you delete the Contract". A conversation can now be deleted too; the wording was left as it was.
