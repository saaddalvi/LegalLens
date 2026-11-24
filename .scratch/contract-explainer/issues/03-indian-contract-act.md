# 03: Add the Indian Contract Act 1872 to the Corpus

**What to build:** The Indian Contract Act 1872 becomes an Act in the Corpus, so Flagged clauses such as a post-employment non-compete (s.27) or a penalty clause (s.74) have a Provision to cite (see `../spec.md`, "Corpus is unchanged in kind"). It goes through the existing ingestion path: a pinned, hash-checked source in `ingestion/sources.py`, an adapter (reuse the Gazette or India Code adapters if the source fits), one Chunk per Provision with long Provisions split per ADR 0002, Status `in_force`, and a verification script like `scripts/verify_everyday_acts.py`. `/law` lists it, and the landing page's covered-Acts list includes it.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] `build_corpus` prints the Contract Act's Chunk count and fails if the count or a Chunk looks wrong
- [ ] Ingestion test on a fixture slice: sections 27 and 74 come out with the right numbers and text, with page furniture and marginal titles removed
- [ ] Verification script checks section totals against the published Act and records what it could not verify, as the everyday-Acts notes do
- [ ] `/law` shows the Act, and a retrieval smoke check for "is a non-compete after leaving a job valid" returns s.27 in the top 10
- [ ] Existing evaluation numbers do not drop (re-run the golden set and note the result)
