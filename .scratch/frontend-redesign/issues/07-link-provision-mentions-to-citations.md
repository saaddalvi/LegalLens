# 07: Follow-up: link Provision mentions in answers to their Citation cards

**What to build:** When an answer mentions a cited Provision in its text (for example "BNS 103" or "Article 21"), the mention becomes a chip the user can click to scroll to that Citation card and open it. The user then gets from a claim to its statute text in one step.

**Decisions (triage):**
- **Matching lives in the frontend** (`frontend/src/lib/mentions.ts`), against the answer's own Citation list. The `/ask` payload stays unchanged (spec stories 43 and 44), and only cited Provisions can become chips, so a chip always has a card to open.
- **Patterns:** Act alias plus number ("BNS 103", "IPC section 302"), number first ("section 103 of the BNS", "धारा 103 BNS"), and "Article N" / "अनुच्छेद N" for the Constitution. Act names are not translated in answers, so one alias table serves English and Hindi. The table mirrors `ACT_ALIASES` in `backend/src/legallens/refs.py`.
- **During the reveal** the text is plain. Chips appear once the text has settled, together with the Citation cards.
- **Click:** opens the card (it never toggles it shut), scrolls to it and moves focus to it.

**Known limits:** Devanagari numerals (१०३) are not matched. "Article N" is always read as the Constitution. The alias table is duplicated from the backend.

**Blocked by:** 05 (Smooth answer reveal)

**Status:** done

- [x] Mentions of cited Provisions become chips that open their Citation card
- [x] Works for Hindi answer text; uncited Provisions are not linked
