# 14: Fix evaluation quality problems found in the first runs

**What to build:** The first full evaluation runs exposed three problems that stop the results from being trusted. Hindi Queries scored 20% accuracy in both modes. Several English labour and criminal-procedure cases missed their expected Provision in both modes. The report misstates case counts when the two modes errored on different cases, and its citation-validity figure is 100% by construction because the endpoint blocks Hallucinated citations before they reach the response. Diagnose each, fix the cause (retrieval, judge or golden-set expectation), and make the report honest.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] Hindi: the cause of the low accuracy is found (retrieval of English Provisions from a Hindi Query, the judge, or the golden-set expectations) and fixed; the Hindi golden cases improve measurably
- [x] English: every case that missed its expected Provision in both modes is classified as a real retrieval gap or a wrong expectation; wrong expectations are corrected in the golden set and real gaps are fixed in retrieval
- [x] The report shows case counts per mode, so a mode that errored on different cases is not misreported
- [x] The report also shows the Hallucinated-citation rate before the endpoint blocks them, next to the post-block citation validity
- [x] Report changes are covered by a test at the `run_evaluation()` seam; retrieval fixes have an endpoint test where a correct seam exists

## Findings

- **Hindi (cause: Citations, not retrieval or judge).** Gemini put the number in the Act field ("Consumer Protection Act 35", number "1, 2, 3, 4"), so the Hallucinated-citation check blocked 60-75% of Hindi answers, which became `none` "cannot answer" messages. Fixed by listing Provisions as `[Act: … | Section: …]` and describing the two Citation fields in the schema. Hindi cases only, same Corpus: accuracy 20% to 60%, hit-rate 20% to 60%, pre-block Hallucinated citations 60-75% to 0%.
- **English misses**: 8 of 26 English, Hindi and repealed-code cases missed their expected Provision in retrieval.
  - Wrong expectation (1 English, 1 Hindi): arrest rights. BNSS 47 and 48 are correct answers; added to the golden set next to Constitution Art. 22.
  - Rank 6-10 (2 cases): wages payment, working hours. `TOP_K` raised from 5 to 10.
  - Real gaps remaining (4; ticket 15's rerun also missed overtime wages `en-wages-overtime` in both modes, so 5 in total: theft BNS 303, FIR BNSS 173, electronic evidence BSA 63, Hindi wages): the expected Provision ranks 11 to beyond 100 under `multilingual-e5-small`. A hybrid dense + BM25 search was tried and did not move any of them, so it was not kept. A larger embedding model (ADR 0003) is the likely fix; left for ticket 15 to re-measure, or a new ticket.
- Report: case counts per mode in each table heading; new "Hallucinated citations before blocking" row, measured by wrapping the LLM at the `run_evaluation()` seam.
- **Retrieval gaps, second pass.** Measured the rank of each expected Provision over the 26 English, Hindi and repealed-code cases (hit = in the top 10): `multilingual-e5-small` 18, `-base` 17, `-large` 18, hybrid search no change, Act name added to the chunk text 18. Gemini embeddings were not measured (free tier cannot embed the Corpus in a day, and the user chose not to use them). The cause is the chunk length: the model reads about 512 tokens and BNS 303, BNSS 173 and BSA 63 are 3.5-6 KB. Fix: Provisions over 800 characters are split at line ends into pieces, searched by best piece, returned whole (ADR 0002 amendment). Result: 20 of 26 (windows of 500 also gave 20, 300 gave 17, 1500 gave 19). Theft BNS 303 went from rank 15 to 2. Tests: `tests/test_long_provisions.py`, at the `/ask` endpoint.
- **Still missing (not fixed here):** FIR (BNSS 173, rank 25), electronic evidence (BSA 63, rank 17) and Hindi wages (rank 13) are just outside the top 10, as are three repealed-code cases that rely on naming a section. Raising `TOP_K` further or re-ranking could reach them; left as known limitations. The full Gemini evaluation was not rerun; ticket 15's figures predate this change.

## Resolution

The three remaining gaps (FIR BNSS 173, electronic evidence BSA 63, Hindi wages) were fixed by adopting Qwen3-Embedding-0.6B in ticket 16 (23 of 26 retrieval cases, up from 20). Three repealed-code cases that rely on naming a section remain known limitations. Qwen3 regresses Hindi tenancy deposit; see ticket 16.
