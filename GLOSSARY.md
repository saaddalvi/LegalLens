# LegalLens

An assistant that answers laypeople's questions about Indian law in English or Hindi, grounded in statute text and backed by verifiable citations.

## Language

### Law

**Act**:
A statute or code in the Corpus, such as the Bharatiya Nyaya Sanhita or the Constitution.
_Avoid_: Law, code (as a generic noun), statute

**Provision**:
A single numbered unit of an Act: a Section, or an Article in the Constitution.
_Avoid_: Clause, rule, entry

**Status**:
Whether a Provision is in force or repealed.
_Avoid_: State, validity

**Superseding provision**:
The in-force Provision that replaced a repealed one, for example BNS 103 for IPC 302.
_Avoid_: Equivalent, new version

### Retrieval

**Corpus**:
The full set of Provisions LegalLens can answer from.
_Avoid_: Knowledge base, dataset, index

**Chunk**:
One Provision as stored for retrieval, with its Act, chapter, number and Status.
_Avoid_: Passage, document, snippet

**Query**:
The question a user asks, in English or Hindi.
_Avoid_: Prompt, request

### Corrective loop

**Verdict**:
The Grader's judgement of retrieved Chunks against a Query: correct, ambiguous or incorrect.
_Avoid_: Score, grade

**Fallback**:
The web search used when a Verdict says the Corpus did not answer the Query.
_Avoid_: Backup, external search

**Trust label**:
The marker on an answer saying whether its support came from the Corpus or from the Fallback.
_Avoid_: Confidence, source tag

### Answer

**Citation**:
A reference in an answer to a specific Provision, with its verbatim English text.
_Avoid_: Reference, source, footnote

**Hallucinated citation**:
A Citation that names a Provision not present in the Corpus.
_Avoid_: Bad cite, fake source

**Out-of-scope query**:
A Query that is not about Indian law or that asks for personal advice, such as whether to sue or sign.
_Avoid_: Invalid query, off-topic
