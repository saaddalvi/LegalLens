# 05: CRAG loop with web Fallback

**What to build:** Retrieved Chunks are graded into a Verdict (correct, ambiguous, incorrect). Correct generates from Chunks only. Incorrect rewrites the Query and uses the general web Fallback. Ambiguous combines Chunks with Fallback results. The response carries a Trust label and lists Fallback sources. A Fallback failure degrades to a Corpus-only answer or an explicit "cannot answer".

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Endpoint tests with faked Gemini and Fallback: each Verdict produces the expected Trust label and sources
- [ ] Endpoint test: Fallback failure degrades gracefully without an error to the user
- [ ] A poor first retrieval triggers a rewritten Query, observable through the Fallback receiving the rewritten text
- [ ] Web provider and Verdict thresholds are chosen and recorded (open item from the spec)
- [ ] A plain-RAG mode (no Grader, no Fallback) is available for the evaluation comparison
