# 15: Full evaluation rerun and README refresh

**What to build:** A clean full evaluation run on the fixed harness, with its results replacing the preliminary figures in the README. The README states plainly whether CRAG beats plain RAG, per metric and per category.

**Blocked by:** 14: Fix evaluation quality problems found in the first runs

**Status:** done

- [x] The full golden set runs in both modes with no case runs excluded for Gemini errors, or every exclusion is explained
- [x] The README results table and notes are replaced with the new figures, including the pre-block Hallucinated-citation rate
- [x] The README says honestly where CRAG is ahead, level or behind plain RAG
- [x] Ticket 11 is marked done

## Comments

Closed with ticket 14 still open for its retrieval gaps (5 cases, see its Findings). The rerun does not depend on those being fixed: they are reported in the README as remaining gaps. Re-measure after any embedding change.
