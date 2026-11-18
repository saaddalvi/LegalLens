# 06: Copy answer button

**What to build:** People will paste answers into WhatsApp or an email. A "Copy answer" button beside the Trust label copies the answer, its Citations, any web sources and the not-legal-advice disclaimer as plain text, so the caveat travels with the answer.

**Status:** done

- [x] `answerAsText` lists the answer, then Citations (repealed ones with what replaced them, model-Act ones as not in force by itself), then web sources, then the disclaimer; empty sections are left out
- [x] Component test: clicking Copy answer writes that text to the clipboard and announces "Copied" in a polite live region
- [x] Component test: a clipboard that rejects, or is missing, announces "Could not copy"
- [x] Component test: a refusal has no Copy answer button
- [x] The disclaimer wording lives in one place (`DISCLAIMER`) and the asking screen's header uses it
- [x] The response types moved to `src/lib/ask-types.ts`, to be shared by the Provision pages (ticket 09)
- [x] Checked in a browser on a real answer (desktop width, light): the button sits beside the Trust label, "Copied" is announced, and the clipboard holds the answer, the Citation lines and the disclaimer
- [ ] Not yet checked by hand: the `/ask` page at phone width and in dark mode (the `/law` pages were, in ticket 09)
