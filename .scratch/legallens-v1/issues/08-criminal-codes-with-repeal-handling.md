# 08: Criminal codes with repeal handling

**What to build:** IPC, CrPC, IEA and BNS, BNSS, BSA are ingested with Status and Superseding-provision metadata. Answers and the UI show a repeal notice and point to the current Provision, for example IPC 302 to BNS 103. Queries about current offences cite the in-force BNS Provision and mention the old IPC equivalent where known.

**Blocked by:** 03

**Status:** ready-for-human

- [x] Ingestion tests on fixture text for each of the six Acts
- [x] Repealed-to-superseding mapping is stored and tested on known examples
- [x] Endpoint test: a Query citing an old IPC section surfaces the BNS Superseding provision
- [x] Endpoint test: a plain-words Query about a current offence cites the in-force Provision
- [x] The frontend shows Status and a repeal notice on affected Citations
- [ ] Per-Act counts are reported (done, ranges provisional) and verified against India Code (open)

## Comments

- Real ingestion is blocked: the official Act PDFs could not be fetched (India Code returned 504; no clean open dataset exists for BNS, BNSS, BSA or the old-to-new mapping). Built on fixtures instead: parsers accept one section-record format (`section`, `chapter`, `text`), so each real source needs an adapter yielding it. Still to do: obtain the six official PDFs plus the MHA IPC-BNS, CrPC-BNSS and IEA-BSA comparison tables, write adapters, replace `tests/fixtures/criminal_code_mappings.json` (fixture only) with the real mapping in `backend/sources/`, wire them into `build_corpus.main`, and confirm the provisional count ranges in `CRIMINAL_ACTS` against India Code.
