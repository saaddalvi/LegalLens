# 08: "Stamp pad" visual identity for `/` and `/ask`

**What to build:** Replace ticket 02's look with one taken from Indian legal material. The old look had a paper background, ink-blue text, a saffron accent, Fraunces, Geist and Noto Sans Devanagari, and every section was a box with a border.

- **Bare-act pages.** Headings sit as marginal notes beside their text, and statute text is set in a book serif.
- **Violet stamp-pad ink.** It marks only what LegalLens has checked against the Corpus: the Trust label stamp, the rule on a verified Citation, and Provision mentions.
- **Red tape.** It marks only what is struck out (repealed Provisions) or failed (Stages, errors).
- **Dark mode is carbon paper.** Every token is redefined under `prefers-color-scheme: dark`.

Type: Tiro Devanagari Hindi for the law (answers, Citations, the hero specimen), and Anek Latin and Anek Devanagari for the interface, with condensed headings from Anek's width axis. Both families cover Latin and Devanagari.

The landing hero is the memorable element: a typeset BNS 103(1) specimen, with IPC 302 struck through and the "From statute text" stamp, linking to that answer. The text was checked against `bns_gaz.pdf`. The only orchestrated motion is the Trust label stamp pressing onto a settled answer, and it is turned off under reduced motion. Behaviour and accessible names do not change.

**Blocked by:** 06 (Landing page), 07 (Link Provision mentions)

**Status:** done

- [x] Tokens are `paper`, `ledger`, `ink`, `muted`, `rule`, `stamp`, `redtape` and `warn*`, with a dark-mode set. No component uses the old `primary`, `accent`, `surface`, `border` or `danger` tokens
- [x] Tiro Devanagari Hindi and Anek are loaded with `next/font`. Hindi answers and Stages render in them
- [x] The Trust label is a shared `Stamp` component, used on answers and in the landing page's Trust label section
- [x] The repealed criminal codes are struck through in the landing page's Corpus list, with their replacement named
- [x] Stage state stays in the text for screen readers ("done", "in progress", "failed")
- [x] Existing tests pass unchanged. A new test checks that the specimen links to its answer
- [x] Manual check: `/` and `/ask` in light and dark, at 1280px and 375px with no horizontal scroll, plus a Hindi answer
- [x] Lint, typecheck and tests pass
