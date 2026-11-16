# 09: Consumer, tenancy and labour Acts

**What to build:** The exact list of consumer, tenancy and labour Acts is agreed with the user, then ingested, so everyday-law Queries such as an unreturned rental deposit or a consumer complaint are answered with Citations.

**Blocked by:** 03

**Status:** ready-for-agent

- [x] The Act list is proposed to the user and approved before ingestion begins
- [x] Ingestion tests on fixture text for each chosen Act format
- [ ] Per-Act counts are reported and verified against India Code
- [x] Endpoint tests: an informal tenancy Query, a consumer Query and a labour Query each cite a relevant Provision

## Notes

- Approved Act list: Consumer Protection Act 2019; Transfer of Property Act 1882, Chapter V (leases) only; the four Labour Codes (Wages, Industrial Relations, Social Security, OSH). 7 Acts with the Model Tenancy Act added afterwards at the user's request, 648 Chunks.
- "Per-Act counts reported and verified against India Code" is only partly met, so it stays unchecked. `backend/scripts/verify_everyday_acts.py` checks counts, numbering and chapter totals against the Acts' published totals, and the Code on Social Security's section numbers against the India Code index. India Code returned 504s for the other Acts, so their text has not been diffed against it. See `backend/sources/everyday_acts.json`.
- Rental deposits: the Model Tenancy Act 2021 (47 clauses; deposit cap and refund in clause 11) was added at the user's request, and a deposit Query now retrieves it. It is a template for States, not law in force by itself, so its Chunks carry the `model` Status (ticket 13), under the Act name 'Model Tenancy Act'.
