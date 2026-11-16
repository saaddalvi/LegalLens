# 04: Hallucinated-citation check

**What to build:** Every Citation in a generated answer is verified against the Corpus. An answer containing a Hallucinated citation never reaches the user: it is regenerated or blocked with a clear message.

**Blocked by:** 02

**Status:** done

- [x] Endpoint test with a faked Gemini that cites a Provision absent from the Corpus: the response contains no such Citation
- [x] Endpoint test: valid Citations pass through unchanged
- [x] Behaviour when regeneration also fails is defined and tested (clear "cannot answer reliably" outcome)
- [x] The check is reusable by the evaluation harness to report citation validity
