# 04: Upload a Contract, split it into Clauses and list it

**What to build:** A signed-in user uploads an English Contract at `/contracts` and watches the Stages. The Contract is then stored, split into Clauses, indexed in pgvector and listed (see `../spec.md`, "Upload endpoint", "Reading the file", "Contract check" and "Splitting into Clauses"). `POST /contracts/stream` accepts a PDF (including scans, read by Gemini), a DOCX or pasted text. It streams the `reading`, `contract_check`, `splitting` and `indexing` Stages and ends with an `answer` event carrying the Contract's id, title and Clause count. Uploads over about 30 pages, uploads that aren't a Contract and Contracts that aren't in English are refused with a stated reason, and nothing is stored. The original file is never written to disk or the database. Migrations add `contracts` and `clauses` (with a 1024-dimension embedding), both cascading from `users`. `GET /contracts` lists the user's own Contracts, and `/contracts` renders the list and the upload box (file picker with drag and drop, plus a paste tab). The Contract brief is ticket 05. For now, opening a Contract shows its Clauses.

**Blocked by:** 02 (Neon baseline)

**Status:** ready-for-agent

- [x] Unit tests for splitting on fixture Contracts: numbered, nested (7.2, 7(a)), unnumbered paragraphs, recitals as Clause 0, and a long Clause split into pieces that keep its number
- [x] Endpoint tests for the Stage sequence of a valid upload, and for each refusal (not a Contract, Hindi, over-long). Refusals store nothing
- [x] Endpoint test: Clause vectors are stored for each piece, and retrieval filtered by one Contract never returns another Contract's Clauses
- [x] Endpoint test: `GET /contracts` returns only the caller's Contracts. Another user's Contract id gets 404
- [x] Contract text never appears in the request log line or in error messages
- [x] Component tests: upload Stages in order, refusal messages, and the list after a successful upload
- [x] Manual check: a scanned rent agreement on stamp paper uploads, and its Clause numbers match the paper
- [x] Lint, typecheck and tests pass

**Implementation notes:** all automated checks pass, including the Postgres-backed tests in `backend/tests/test_contracts.py`. Manual check done on a scanned rent agreement: Clauses 1 to 21 match the paper, with the parties and recitals as Clause 0. Known limitation: text after the last Clause (Annexure, "In witness whereof", witness and signature lines) is folded into the last Clause, because the witnesses' "1." and "2." repeat numbers already used.
