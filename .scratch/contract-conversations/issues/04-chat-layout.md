# 04: Chat layout for a Contract conversation

**What to build:** The open conversation reads like a chat (Claude, ChatGPT) but keeps LegalLens's look: no chat bubbles (see `../spec.md`, "UI"). The question box stays at the bottom of the viewport while a conversation is open. Sending a Query scrolls it to the top of view, and its Stages and answer appear below it. Enter sends and Shift+Enter adds a new line (an IME composition in progress must not send). An empty conversation shows up to three starter questions. They're filled from a fixed English template using the first Flagged clauses' numbers and, where the Clause has one, its heading: for example "What does Clause 9 (Security deposit) say, and what does Indian law provide?". If there are fewer than three Flagged clauses, a fixed generic set fills the rest (for example "What must I do under this Contract?" and "How can this Contract be ended?"). Clicking one asks it. No model call is made to build them. Keep the existing behaviour: a new Query cancels one in flight ("Ask this instead"), "Try again" works on failure, and saved answers show at once while new ones are revealed word by word.

**Use the `impeccable` skill for all UI work in this issue**, following `DESIGN.md` and `PRODUCT.md`.

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] Component test: Enter submits, Shift+Enter inserts a new line, and Enter during IME composition does nothing
- [ ] Component test: sending scrolls the new question into view
- [ ] Component test: an empty conversation shows starter questions from the Flagged clauses, and clicking one sends it
- [ ] Component test: a Contract with no Flagged clauses shows the generic starters, and one with a single Flagged clause shows it plus two generic ones
- [ ] Existing conversation tests still pass (cancel in flight, Try again, word-by-word reveal only for new answers)
- [ ] The fixed question box never covers the last answer, its Citations or its Clause references, at phone width or desktop
- [ ] Keyboard and screen-reader pass: focus order, the "You asked" labels, and focus moving to the box after an answer
- [ ] Checked at phone width (375px) and desktop, in light and dark
- [ ] Lint, typecheck and tests pass
