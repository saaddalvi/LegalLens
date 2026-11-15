# 08: Criminal codes with repeal handling

**What to build:** IPC, CrPC, IEA and BNS, BNSS, BSA are ingested with Status and Superseding-provision metadata. Answers and the UI show a repeal notice and point to the current Provision, for example IPC 302 to BNS 103. Queries about current offences cite the in-force BNS Provision and mention the old IPC equivalent where known.

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] Ingestion tests on fixture text for each of the six Acts
- [ ] Repealed-to-superseding mapping is stored and tested on known examples
- [ ] Endpoint test: a Query citing an old IPC section surfaces the BNS Superseding provision
- [ ] Endpoint test: a plain-words Query about a current offence cites the in-force Provision
- [ ] The frontend shows Status and a repeal notice on affected Citations
- [ ] Per-Act counts are reported and verified against India Code
