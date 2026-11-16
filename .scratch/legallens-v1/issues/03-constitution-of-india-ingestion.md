# 03: Constitution of India ingestion

**What to build:** The Constitution is parsed into one Chunk per Article with Act, chapter, number, text and Status, verified against India Code, and loaded into the vector store. Real constitutional Queries then return real Citations.

**Blocked by:** 02

**Status:** done

- [x] Ingestion tests (seam 2) on fixture text: correct Article boundaries, numbering edge cases (for example lettered Articles), and metadata
- [x] A one-command build produces the Corpus reproducibly
- [x] The build reports Chunk counts per Act and flags counts that look wrong
- [x] Source text is checked against India Code and any patches are recorded
- [x] Endpoint test: a constitutional Query against the built Corpus cites the expected Article
