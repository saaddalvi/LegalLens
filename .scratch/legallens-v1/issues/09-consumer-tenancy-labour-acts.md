# 09: Consumer, tenancy and labour Acts

**What to build:** The exact list of consumer, tenancy and labour Acts is agreed with the user, then ingested, so everyday-law Queries such as an unreturned rental deposit or a consumer complaint are answered with Citations.

**Blocked by:** 03

**Status:** ready-for-agent

- [x] The Act list is proposed to the user and approved before ingestion begins
- [x] Ingestion tests on fixture text for each chosen Act format
- [ ] Per-Act counts are reported and verified against India Code
- [x] Endpoint tests: an informal tenancy Query, a consumer Query and a labour Query each cite a relevant Provision

## Notes

- Approved Act list: Consumer Protection Act 2019; Transfer of Property Act 1882, Chapter V (leases) only; the four Labour Codes (Wages, Industrial Relations, Social Security, OSH). 6 Acts, 601 Chunks.
- "Per-Act counts reported and verified against India Code" is only partly met, so it stays unchecked. `backend/scripts/verify_everyday_acts.py` checks counts, numbering and chapter totals against the Acts' published totals, and the Code on Social Security's section numbers against the India Code index. India Code returned 504s for the other Acts, so their text has not been diffed against it. See `backend/sources/everyday_acts.json`.
- The approved list has no security-deposit provision (the Transfer of Property Act says nothing on deposits), so a "my landlord won't return my deposit" Query retrieves poorly. The Model Tenancy Act 2021 or a state rent Act would cover it; add one to close that gap.
