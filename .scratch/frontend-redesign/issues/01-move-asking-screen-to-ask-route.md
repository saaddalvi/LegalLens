# 01: Move the asking screen to `/ask`, with the Query in the address

**What to build:** This is the prefactor for the redesign (see `../spec.md`). The asking screen moves from the site root to its own `/ask` route with no change in behaviour. The route reads the `q` search parameter on the server and passes it to the client asking component as an `initialQuery` prop, which submits it at once. Every submitted Query updates `q` in the address with a new history entry, so a Query can be bookmarked or shared and back and forward move between Queries. Until the landing page lands (ticket 06), `/` redirects to `/ask`.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] `/ask` shows the current asking screen: disclaimer, ask box, answer card with Trust label, Citations and web sources, refusals, loading and error states
- [x] Opening `/ask?q=<Query>` fills the ask box and submits the Query without pressing Ask
- [x] Submitting a Query updates `q` in the address with a history entry. Back returns to the previous Query and shows its answer again
- [x] `/` redirects to `/ask`
- [x] The existing page component tests are moved to the asking component and pass unchanged in what they assert
- [x] New component tests: rendered with `initialQuery`, the component submits it (the `fetch` stub is called with that Query). Rendered without it, nothing is submitted
- [x] Lint, typecheck and tests pass
