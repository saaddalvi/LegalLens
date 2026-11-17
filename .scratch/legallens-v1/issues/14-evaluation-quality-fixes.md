# 14: Fix evaluation quality problems found in the first runs

**What to build:** The first full evaluation runs exposed three problems that stop the results from being trusted. Hindi Queries scored 20% accuracy in both modes. Several English labour and criminal-procedure cases missed their expected Provision in both modes. The report misstates case counts when the two modes errored on different cases, and its citation-validity figure is 100% by construction because the endpoint blocks Hallucinated citations before they reach the response. Diagnose each, fix the cause (retrieval, judge or golden-set expectation), and make the report honest.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Hindi: the cause of the low accuracy is found (retrieval of English Provisions from a Hindi Query, the judge, or the golden-set expectations) and fixed; the Hindi golden cases improve measurably
- [ ] English: every case that missed its expected Provision in both modes is classified as a real retrieval gap or a wrong expectation; wrong expectations are corrected in the golden set and real gaps are fixed in retrieval
- [ ] The report shows case counts per mode, so a mode that errored on different cases is not misreported
- [ ] The report also shows the Hallucinated-citation rate before the endpoint blocks them, next to the post-block citation validity
- [ ] Report changes are covered by a test at the `run_evaluation()` seam; retrieval fixes have an endpoint test where a correct seam exists
