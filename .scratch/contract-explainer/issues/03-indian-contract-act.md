# 03: Add the Indian Contract Act 1872 to the Corpus

**What to build:** The Indian Contract Act 1872 becomes an Act in the Corpus, so Flagged clauses such as a post-employment non-compete (s.27) or a penalty clause (s.74) have a Provision to cite (see `../spec.md`, "Corpus is unchanged in kind"). It goes through the existing ingestion path: a pinned, hash-checked source in `ingestion/sources.py`, an adapter (reuse the Gazette or India Code adapters if the source fits), one Chunk per Provision with long Provisions split per ADR 0002, Status `in_force`, and a verification script like `scripts/verify_everyday_acts.py`. `/law` lists it, and the landing page's covered-Acts list includes it.

**Blocked by:** None (can start immediately).

**Status:** done (text not diffed against India Code or the Department file; see Notes)

- [x] `build_corpus` prints the Contract Act's Chunk count and fails if the count or a Chunk looks wrong
- [x] Ingestion test on a fixture slice: sections 27 and 74 come out with the right numbers and text, with page furniture and marginal titles removed
- [x] Verification script checks section totals against the published Act and records what it could not verify, as the everyday-Acts notes do
- [x] `/law` shows the Act, and a retrieval smoke check for "is a non-compete after leaving a job valid" returns s.27 in the top 10
- [x] Existing evaluation numbers do not drop (re-run the golden set and note the result)

## Notes

- **Source.** India Code answers with 504s (tried 24 November 2026), so the text is the Legislative Department's bare-act PDF as mirrored by Drishti Judiciary, pinned by sha256 as `contract_act_ld.pdf` in `backend/data/raw/everyday/`. A first candidate (the UP commercial-tax department's copy) was rejected: it has inserted "Related Judgements" blocks and garbled words. The mirror is a third party, and its body text has not been diffed against an independent copy.
- **Count.** 192 Chunks: sections 1-75 and 124-238 with 19A and 178A. Chapter VII (sale of goods, 76-123) and Chapter XI (partnership, 239-266) are repealed and have no text, so they are not Provisions. The Corpus is now 3,693 Chunks across 15 Acts. `verify_everyday_acts.py` checks the numbering and the print's own contents list (same 192 sections, same order).
- **Retrieval.** `scripts/smoke_retrieval.py`: "is a non-compete after leaving a job valid" returns s.27 at rank 10 (narrow); a penalty Query returns s.74 at rank 3.
- **Evaluation (2026-11-24).** The LLM-scored numbers came out lower than the committed report (Plain RAG accuracy 80% against 86%, CRAG 89% against 94%; one Plain-RAG case, en-const-arrest, failed on Gemini 503 "high demand" after retries and is excluded). Raw retrieval did not change: 23 of 26 cases still have an expected Provision in the top 10, the figure recorded in ADR 0003, and the Contract Act appears in the top 10 of one golden case only (en-tpa-lease, which still hits). The case-level changes (en-wages-overtime, hi-const-arrest, hi-mta-deposit, en-ir-strike, poor-*) are in cases whose top 10 holds no Contract Act chunk, so they are model, grader and 503 variance, not the Corpus change. `evaluation/report.md` was not overwritten; a clean re-run when Gemini is not overloaded would settle it.
