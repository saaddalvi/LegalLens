# 14: Fix evaluation quality problems found in the first runs

**What to build:** The first full evaluation runs exposed three problems that stop the results from being trusted. Hindi Queries scored 20% accuracy in both modes. Several English labour and criminal-procedure cases missed their expected Provision in both modes. The report misstates case counts when the two modes errored on different cases, and its citation-validity figure is 100% by construction because the endpoint blocks Hallucinated citations before they reach the response. Diagnose each, fix the cause (retrieval, judge or golden-set expectation), and make the report honest.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent (remaining: the 4 real retrieval gaps below)

- [x] Hindi: the cause of the low accuracy is found (retrieval of English Provisions from a Hindi Query, the judge, or the golden-set expectations) and fixed; the Hindi golden cases improve measurably
- [ ] English: every case that missed its expected Provision in both modes is classified as a real retrieval gap or a wrong expectation; wrong expectations are corrected in the golden set and real gaps are fixed in retrieval
- [x] The report shows case counts per mode, so a mode that errored on different cases is not misreported
- [x] The report also shows the Hallucinated-citation rate before the endpoint blocks them, next to the post-block citation validity
- [x] Report changes are covered by a test at the `run_evaluation()` seam; retrieval fixes have an endpoint test where a correct seam exists

## Findings

- **Hindi (cause: Citations, not retrieval or judge).** Gemini put the number in the Act field ("Consumer Protection Act 35", number "1, 2, 3, 4"), so the Hallucinated-citation check blocked 60-75% of Hindi answers, which became `none` "cannot answer" messages. Fixed by listing Provisions as `[Act: … | Section: …]` and describing the two Citation fields in the schema. Hindi cases only, same Corpus: accuracy 20% to 60%, hit-rate 20% to 60%, pre-block Hallucinated citations 60-75% to 0%.
- **English misses**: 8 of 26 English, Hindi and repealed-code cases missed their expected Provision in retrieval.
  - Wrong expectation (1 English, 1 Hindi): arrest rights. BNSS 47 and 48 are correct answers; added to the golden set next to Constitution Art. 22.
  - Rank 6-10 (2 cases): wages payment, working hours. `TOP_K` raised from 5 to 10.
  - Real gaps remaining (4: theft BNS 303, FIR BNSS 173, electronic evidence BSA 63, Hindi wages): the expected Provision ranks 11 to beyond 100 under `multilingual-e5-small`. A hybrid dense + BM25 search was tried and did not move any of them, so it was not kept. A larger embedding model (ADR 0003) is the likely fix; left for ticket 15 to re-measure, or a new ticket.
- Report: case counts per mode in each table heading; new "Hallucinated citations before blocking" row, measured by wrapping the LLM at the `run_evaluation()` seam.
