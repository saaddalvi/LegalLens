# 05: Contract brief with Flagged clauses

**What to build:** After a Contract is split and indexed, LegalLens writes its Contract brief from the whole Contract text and shows it at `/contracts/[id]` (see `../spec.md`, "Contract brief" and "Answer shape"). The upload stream gains the `brief`, `citation_check` and `citation_recheck` Stages. The brief is structured JSON: parties, purpose, key terms (each with a Clause number), each party's obligations, and Flagged clauses (Clause number, how it differs, Citations). Provisions relevant to candidate flags are retrieved from the Corpus. Every Clause reference is checked against the stored Clauses, and every Citation goes through the existing Citation check. A Hallucinated clause reference or Hallucinated citation causes one regeneration. After that, any flag still missing a verified Citation or a valid Clause reference is dropped. The brief is stored as the first message of the Contract conversation (migration adds `contract_messages`). The page renders Clause references labelled "Your Contract, Clause N" and Citations linking to `/law`, with the disclaimer always visible.

**Blocked by:** 04 (Upload a Contract). Flags against the Contract Act also need 03.

**Status:** ready-for-agent

- [x] Endpoint test: a valid upload's `answer` event carries a brief whose Clause references all match stored Clause text
- [x] Endpoint test: a fake LLM that flags a Clause with a Hallucinated citation, then again on regeneration, yields a brief without that flag
- [x] Endpoint test: a Hallucinated clause reference on the first generation triggers `citation_recheck` and a valid brief
- [x] Endpoint test: reopening the Contract returns the stored brief without calling the LLM
- [x] The brief never says whether to sign (prompt rule, and an eval case in ticket 08)
- [x] Component tests: all brief sections render, Flagged clauses show both the Clause text and the Citation, and Citations link to `/law`
- [x] Lint, typecheck and tests pass

**Implementation notes:** all automated checks pass (backend 426 tests including the Postgres-backed ones, frontend 121). The brief is written by one `write_brief` call; Provisions given to the model are retrieved per Clause (top 2 for up to 40 Clauses, at most 20 kept). A regeneration repeats the same call without telling the model what failed. An obligation with any invalid Clause number is dropped whole. Contracts uploaded before this ticket have no brief and show their Clauses only.
