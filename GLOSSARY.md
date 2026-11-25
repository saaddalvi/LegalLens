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
Whether a Provision is in force, repealed, or from a model Act (`model`): a template such as the Model Tenancy Act that States may adopt, not law in force by itself.
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
The Grader's judgement of retrieved Chunks or Clauses against a Query: correct, ambiguous or incorrect.
_Avoid_: Score, grade

**Fallback**:
The web search used when a Verdict says the Corpus did not answer the Query.
_Avoid_: Backup, external search

**Stage**:
One step of answering a Query, shown to the user while they wait, such as the scope check, retrieval, grading, the Fallback, generation or the Citation check.
_Avoid_: Step, phase, status (Status is a Provision's in-force state)

**Decisions**:
What the corrective loop decided while answering one Query: the Grader's score and Verdict, how many Fallback sources came back, and whether a Hallucinated citation forced a regeneration or blocked the answer.
_Avoid_: Trace, debug info

**Trust label**:
The marker on an answer saying whether its support came from the Corpus, the Fallback, the user's Contract or a combination, or `none` for a "cannot answer" message or a refusal of an Out-of-scope query, which no source supports.
_Avoid_: Confidence, source tag

### Answer

**Citation**:
A reference in an answer to a specific Provision, with its verbatim English text.
_Avoid_: Reference, source, footnote

**Hallucinated citation**:
A Citation that names a Provision not present in the Corpus.
_Avoid_: Bad cite, fake source

**Out-of-scope query**:
A Query that is not about Indian law or that asks for personal advice, such as whether to sue or sign. Asking what one can do is not personal advice: it is answered with the law and the remedies, without choosing among them. In a Contract conversation, also a Query about neither the Contract nor the law that governs it.
_Avoid_: Invalid query, off-topic

### Contracts

**Contract**:
An agreement between two or more parties that a user uploads to have explained, such as a rent agreement, a job offer or an NDA. Only English Contracts are accepted.
_Avoid_: Document, file, agreement (as the term)

**Clause**:
A single numbered unit of a Contract. A Contract without numbered Clauses has its paragraphs numbered in order.
_Avoid_: Section, Provision, term

**Clause reference**:
A reference in an answer to a specific Clause of the user's Contract, with its verbatim text.
_Avoid_: Citation (a Citation is always to a Provision), quote

**Hallucinated clause reference**:
A Clause reference whose number or text is not in the Contract.
_Avoid_: Bad quote, wrong clause

**Contract brief**:
The structured explanation of a Contract given when it is uploaded: the parties, what the Contract is for, its key terms, what each party must do, and its Flagged clauses.
_Avoid_: Summary, overview, analysis

**Flagged clause**:
A Clause that differs from what Indian law provides, shown with its Clause reference and at least one Citation. LegalLens says how the Clause differs, never whether to sign.
_Avoid_: Red flag, risky clause, unfair clause

**Contract conversation**:
One saved thread of Queries and answers about a Contract, begun by its first Query and titled with it. A Contract has zero or more, and each is answered with only its own earlier turns as context. The Contract brief belongs to the Contract, not to any Contract conversation.
_Avoid_: Chat, thread, session

**Follow-up**:
A Query in a Contract conversation that relies on earlier turns of that conversation for its meaning, such as "what about the notice period for that?"
_Avoid_: Reply, continuation
