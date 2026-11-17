# 07: Follow-up: link Provision mentions in answers to their Citation cards

**What to build:** When an answer mentions a cited Provision in its text (for example "BNS 103" or "Article 21"), the mention becomes a chip the user can click to scroll to that Citation card and open it. The user then gets from a claim to its statute text in one step. The frontend redesign left this out of scope (see `../spec.md`, "Out of Scope"). Open questions to settle in triage:
- How to match mentions in English and Hindi answer text against the Citation list. The answer refers to Provisions by Act name and number, and Act names are not translated.
- Whether the matching belongs in the backend (which already parses Provision references in Queries) or the frontend.
- How the chip behaves during the answer reveal.

**Blocked by:** 05 (Smooth answer reveal)

**Status:** needs-triage

- [ ] Triage settles the matching approach and where it lives, then rewrites this ticket's acceptance criteria
