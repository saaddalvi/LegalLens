# 01: Housekeeping

**What to build:** Remove stale state found in the codebase review: an unused dependency, an untracked tool directory, a ticket whose status was out of date, and a refusal whose Trust label did not match the glossary.

**Status:** done

- [x] `langgraph` is removed from `backend/pyproject.toml` (it is never imported)
- [x] `.playwright-mcp/` is gitignored
- [x] Frontend-redesign ticket 04 is marked done
- [x] An Out-of-scope query's refusal has Trust label `none` (it was `corpus`), and the glossary's Trust label entry says so
- [x] Endpoint test: a refused Query returns `trust_label == "none"`
