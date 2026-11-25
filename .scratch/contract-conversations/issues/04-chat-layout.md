# 04: Chat layout for a Contract conversation

**What to build:** The open conversation reads like a chat (Claude, ChatGPT) but keeps LegalLens's look: no chat bubbles (see `../spec.md`, "UI"). The question box stays at the bottom of the viewport while a conversation is open. Sending a Query scrolls it to the top of view, and its Stages and answer appear below it. Enter sends and Shift+Enter adds a new line (an IME composition in progress must not send). An empty conversation shows up to three starter questions. They're filled from a fixed English template using the first Flagged clauses' numbers and, where the Clause has one, its heading: for example "What does Clause 9 (Security deposit) say, and what does Indian law provide?". If there are fewer than three Flagged clauses, a fixed generic set fills the rest (for example "What must I do under this Contract?" and "How can this Contract be ended?"). Clicking one asks it. No model call is made to build them. Keep the existing behaviour: a new Query cancels one in flight ("Ask this instead"), "Try again" works on failure, and saved answers show at once while new ones are revealed word by word.

**Use the `impeccable` skill for all UI work in this issue**, following `DESIGN.md` and `PRODUCT.md`.

**Blocked by:** 03

**Status:** ready-for-human

- [x] Component test: Enter submits, Shift+Enter inserts a new line, and Enter during IME composition does nothing
- [x] Component test: sending scrolls the new question into view
- [x] Component test: an empty conversation shows starter questions from the Flagged clauses, and clicking one sends it
- [x] Component test: a Contract with no Flagged clauses shows the generic starters, and one with a single Flagged clause shows it plus two generic ones
- [x] Existing conversation tests still pass (cancel in flight, Try again, word-by-word reveal only for new answers)
- [x] The fixed question box never covers the last answer, its Citations or its Clause references, at phone width or desktop
- [ ] Keyboard and screen-reader pass: focus order, the "You asked" labels, and focus moving to the box after an answer
- [x] Checked at phone width (375px) and desktop, in light and dark
- [x] Lint, typecheck and tests pass

## Comments

2026-11-25: Implemented in commit 4b7ce67. 260 frontend tests pass, typecheck and eslint are clean, and the production build succeeds. No backend code changed.

Checked in a browser at 375px and 1440px, light and dark, on a copy of the frontend without the sign-in redirect and with a fake API. Not checked against the real backend or a real phone, so the on-screen keyboard is untested.

**Left for a human:** the screen-reader half of the keyboard and screen-reader pass. Tab order was walked in the browser with nothing hidden under the box, and tests cover the "You asked" labels, the focus moves and the "Your answer is ready." announcement, but no screen reader was run.

Choices the ticket left open:

- The box is on screen wherever the reader is on the page, once the conversation has loaded. A Clause link's way back stacks above it.
- On sending from a button that then disappears (a starter or "Try again"), focus goes to the question. After the answer it returns to the box, unless the reader has moved elsewhere.
- Three starters are always shown. The third general one is "What happens if either side breaks this Contract?". A flagged Clause 0 is asked about as "the Recitals".
- A starter names a Clause's heading only when the Clause list shows it as a title. That test also rejects some real titles, such as "Lock-in", or one followed by a numbered sub-clause.

**For a decision:** a starter's heading is Contract text, and a clicked starter is one of the user's own Queries, so under ADR 0006 it can reach the web Fallback's Query. The ticket asks for the heading, so it is included.

