# 16: Test bge-m3 and Qwen3 embedding models against the retrieval gaps

**What to build:** Measure whether a long-input local embedding model finds the expected Provision for the golden-set Queries better than `multilingual-e5-small` with split Provisions (20 of 26 in the top 10). Candidates: `BAAI/bge-m3` and `Qwen/Qwen3-Embedding-0.6B`. Adopt one only if it clearly beats the current result and is affordable to load at startup in the deployed app.

**Blocked by:** None (can start immediately). Follows ticket 14, whose findings and the ADR 0002 and 0003 notes give the baseline.

**Status:** ready-for-human (measurements done; adoption of Qwen3-Embedding-0.6B awaits a decision on deployed-app memory and startup cost)

- [ ] Each model is scored on the 26 English, Hindi and repealed-code cases with expected Provisions, counting a hit when an expected Provision is in the top 10
- [ ] Each model is run two ways: whole Provisions up to its longest input, and 800-character pieces (as the Corpus now stores them)
- [ ] Results are recorded beside the baseline: per-case rank of the expected Provision, hit count, embedding time for the Corpus, and model size on disk
- [ ] Qwen3 query handling is checked (it expects an instruction prompt on Queries) and its support in the installed `sentence-transformers` is confirmed before scoring
- [ ] The three remaining gaps are reported explicitly: FIR (BNSS 173), electronic evidence (BSA 63) and Hindi wages
- [ ] If a model is adopted: it beats 20 of 26 clearly, the Corpus is rebuilt, the embedding change is covered at the existing endpoint seam, ADR 0003 is updated and the README results are rerun. If none is adopted: the findings go in ADR 0003 and the ticket closes

## Notes

- Larger e5 models (base, large), a hybrid dense + BM25 search and the Act name in the chunk text were already tried and did not beat 18 of 26 (ticket 14).
- Gemini embeddings are ruled out: the free tier cannot embed the Corpus in a day, and the choice was made not to use them.
- Weigh cost: bge-m3 and Qwen3-0.6B are about 570-600M parameters, roughly 10 times the current model, so the cost of loading in the deployed app counts against a small gain.
- Avoid models that need `trust_remote_code`.

## Findings

See the ADR 0003 note "Long-input models". Qwen3-Embedding-0.6B scores 23 of 26 (e5-small: 20), bge-m3 22. Qwen3 fixes FIR, electronic evidence and Hindi wages but regresses Hindi tenancy deposit; bge-m3 still misses electronic evidence. Pieces and whole Provisions give the same hit counts. Cost: Qwen3 is about 8 times slower to embed the Corpus than e5-small (189 s vs 24 s) and 1.1 GB vs 449 MB on disk. Not adopted yet: the README does not state the deployed app's memory limit.
