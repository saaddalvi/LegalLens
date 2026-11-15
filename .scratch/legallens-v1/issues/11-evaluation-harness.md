# 11: Evaluation harness

**What to build:** A golden Q&A set with expected Provisions is run through the endpoint against the real Corpus in both plain-RAG and CRAG modes. A report compares retrieval hit-rate, answer accuracy and citation validity side by side.

**Blocked by:** 05, 07, 08, 09

**Status:** ready-for-agent

- [ ] The golden set includes English, Hindi, repealed-code, out-of-scope and poor-retrieval cases across all Acts in the Corpus
- [ ] One command runs the evaluation and writes a readable report
- [ ] Citation validity uses the Hallucinated-citation check from ticket 04
- [ ] The report shows plain RAG versus CRAG on every metric
- [ ] Results are summarised in the README
