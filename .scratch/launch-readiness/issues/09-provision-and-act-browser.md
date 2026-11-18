# 09: Provision and Act browser

**What to build:** Citations should lead to the law itself. Pages under `/law` show every Act, an Act's Provisions grouped by chapter, and one Provision in full, with permanent, shareable addresses. The "current law is BNS 103" note on a repealed Provision becomes a link, and so does "Replaces IPC 302".

**Status:** done

- [x] Backend: `GET /acts` (each Act with its count), `GET /acts/{act}` (its Provisions in statute order, with a first-line snippet), `GET /provision/{act}/{number}` (the whole Provision, number case-insensitive); none rate limited, since they make no Gemini calls
- [x] Statute order: "21A" after "21" and before "22" in every one of the 14 Acts (checked against the real 3,501-Provision Corpus)
- [x] Frontend pages `/law`, `/law/[act]`, `/law/[act]/[number]`, with a friendly not-found page and a Try again error page for a sleeping backend
- [x] The repealed, superseding and model-Act notes are one shared component (`provision-notes.tsx`), used by Citation cards and the Provision page; their references are links
- [x] Each Citation card has an "Open full Provision" link; the landing page's Act list links to each Act; a Provision page offers "Ask LegalLens about this Provision"
- [x] Tests: backend endpoints (`tests/test_browse.py`), the views and the reference parser, the landing page's links, and the Citation card's links
- [x] `next build` passes with no backend running (the `/law` routes are partially prerendered and read the backend per request, never at build time)
- [x] Checked by hand in a browser against the real Corpus: all 499 Constitution Articles in order with `21A` after `21`; an Act name containing a comma; a missing Provision; the Acts index; phone width without horizontal scroll; dark mode; a real answer's Citation link, then its "Replaces" link back to IPC 302

## Notes

- This Next.js version differs from older ones: `params` is a Promise, an error page receives `retry` (not `reset`), and with Cache Components request-time data must sit inside `Suspense`. The pages follow the bundled docs (`node_modules/next/dist/docs`).
- No `generateStaticParams`: it would make a Vercel build depend on the backend being reachable. Reads are cached for an hour per Act or Provision instead (`'use cache'`); a "not found" is cached too, any other failure is not.
- The stored Provision text carries line breaks from the source PDF's layout, so the text is not shown with `white-space: pre-line` (that split sentences mid-way). Sub-clauses therefore run together, as they already do in Citation cards.
- A missing Provision shows the not-found page but the HTTP status is 200, because the page has already started streaming (Next adds `noindex`).
- Every `/law` page has the same browser tab title, "Browse the law | LegalLens". A per-page title needs `generateMetadata` reading the route params, which Cache Components makes delicate; left for later.
- Status codes of Citation links assume the frontend and backend are both up; the Space sleeps when idle, so the first visit can show "Loading…" for a while.
