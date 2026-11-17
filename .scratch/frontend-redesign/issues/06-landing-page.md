# 06: Landing page at `/`

**What to build:** A first-time visitor at the site root finds a landing page that explains LegalLens and lets them ask straight away (see `../spec.md`, "Landing page sections"). This replaces the temporary `/` to `/ask` redirect. The page has five sections, all built with the design system's tokens:

1. A hero: a headline and subheading, the ask box, and example Queries in English and Hindi taken from the golden set's cases that CRAG answers well.
2. How it works, in three steps: you ask, it is checked against the statute text, you get an answer with Citations you can read.
3. What the Corpus covers: the Acts listed by name, with a note that repealed IPC, CrPC and IEA Provisions point to their BNS, BNSS and BSA replacements.
4. Trust labels explained, using the same wording as the labels on answers.
5. The disclaimer and a footer.

The example Queries link to `/ask?q=…`, and the ask box submits to `/ask?q=…`, so the answer starts at once. The page shows no evaluation figures. Interface copy is English. Hindi example Queries carry `lang="hi"`.

**Blocked by:** 01 (Move the asking screen to `/ask`), 02 (Editorial design system)

**Status:** ready-for-agent

- [ ] `/` renders the landing page and no longer redirects
- [ ] Component test: the disclaimer is present
- [ ] Component test: English and Hindi example Queries link to `/ask?q=…` with the Query URL-encoded
- [ ] Component test: submitting the ask box navigates to `/ask?q=…` with the typed Query. Submitting an empty box does nothing
- [ ] Component test: every Act in the Corpus is listed by name, along with the repeal note
- [ ] Component test: the Trust label explanations use the same wording as the labels on answers (one shared source of the wording)
- [ ] There is a clear way to reach `/ask` directly from the landing page
- [ ] Page metadata (title and description) describes LegalLens
- [ ] Manual check in a browser: the landing page looks right in light and dark mode and at phone width with no horizontal scrolling, and clicking an example Query starts its answer on `/ask`
- [ ] Lint, typecheck and tests pass
