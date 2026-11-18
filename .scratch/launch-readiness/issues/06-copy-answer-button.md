# 06: Copy answer button

**What to build:** People will paste answers into WhatsApp or an email. A "Copy answer" button beside the Trust label copies the answer, its Citations, any web sources and the not-legal-advice disclaimer as plain text, so the caveat travels with the answer.

**Status:** done

- [x] `answerAsText` lists the answer, then Citations (repealed ones with what replaced them, model-Act ones as not in force by itself), then web sources, then the disclaimer; empty sections are left out
- [x] Component test: clicking Copy answer writes that text to the clipboard and announces "Copied" in a polite live region
- [x] Component test: a clipboard that rejects, or is missing, announces "Could not copy"
- [x] Component test: a refusal has no Copy answer button
- [x] The disclaimer wording lives in one place (`DISCLAIMER`) and the asking screen's header uses it
- [x] The response types moved to `src/lib/ask-types.ts`, to be shared by the Provision pages (ticket 09)
- [ ] Checked by hand in a browser at phone width and in both colour schemes (not automated; done with the end-to-end check in ticket 07)
