# 08: Criminal codes with repeal handling

**What to build:** IPC, CrPC, IEA and BNS, BNSS, BSA are ingested with Status and Superseding-provision metadata. Answers and the UI show a repeal notice and point to the current Provision, for example IPC 302 to BNS 103. Queries about current offences cite the in-force BNS Provision and mention the old IPC equivalent where known.

**Blocked by:** 03

**Status:** ready-for-human

- [x] Ingestion tests on fixture text for each of the six Acts
- [x] Repealed-to-superseding mapping is stored and tested on known examples
- [x] Endpoint test: a Query citing an old IPC section surfaces the BNS Superseding provision
- [x] Endpoint test: a plain-words Query about a current offence cites the in-force Provision
- [x] The frontend shows Status and a repeal notice on affected Citations
- [ ] Per-Act counts are reported (done) and verified against India Code (open: BNS, BNSS, BSA and CrPC have exact counts and pass the cross-checks in `backend/scripts/verify_criminal_codes.py`, but are not yet compared with India Code; IPC and IEA are not ingested)

## Comments

- Real ingestion is blocked: the official Act PDFs could not be fetched (India Code returned 504; no clean open dataset exists for BNS, BNSS, BSA or the old-to-new mapping). Built on fixtures instead: parsers accept one section-record format (`section`, `chapter`, `text`), so each real source needs an adapter yielding it. Still to do: obtain the six official PDFs plus the MHA IPC-BNS, CrPC-BNSS and IEA-BSA comparison tables, write adapters, replace `tests/fixtures/criminal_code_mappings.json` (fixture only) with the real mapping in `backend/sources/`, wire them into `build_corpus.main`, and confirm the provisional count ranges in `CRIMINAL_ACTS` against India Code.

- Real ingestion for BNS, BNSS, BSA and CrPC (from the pinned PDFs in `backend/data/raw/criminal/`, gitignored): adapters in `ingestion/pdf_text.py` (Gazette and India Code quirks, tested on real excerpts), the NCRB table parser in `ingestion/mapping_tables.py`, hashes and loading in `ingestion/sources.py`, wired into `build_corpus.main` (which now exits 2 if a PDF is missing). Counts: BNS 358, BNSS 531, BSA 170, CrPC 535, now exact in `CRIMINAL_ACTS`. 528 BNSS-CrPC mappings (10 CrPC sections deleted, 9 BNSS sections new) apply cleanly. `backend/sources/criminal_codes.json` records what was checked and the four accepted differences. Run `python scripts/verify_criminal_codes.py` (about 25 s).
- Still open and needs the user: the IPC and the consolidated Indian Evidence Act (the 1872 scan is unusable), a BSA-IEA table, and a BNS-IPC parse (the NCRB BNS table is keyed by sub-section and needs its own parser; it cannot be applied until the IPC is ingested). The last checkbox stays open until all six Acts are verified against India Code, which returned 504s from the agent's machine.
