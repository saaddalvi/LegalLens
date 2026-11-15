# LegalLens v1

Status: ready-for-agent

## Problem Statement

Laypeople in India who face a legal question (a tenancy dispute, a consumer complaint, a workplace issue, an arrest, a constitutional right) cannot easily find the relevant law, understand it, or trust what they read. Statute text is dense and structured differently per Act. Criminal law changed in July 2024, so search results mix repealed Provisions (IPC, CrPC, IEA) with their Superseding provisions (BNS, BNSS, BSA). Generic chatbots answer confidently but invent Provisions, and many users would rather ask in Hindi than English. There is no tool that answers in the user's language, grounds every claim in real statute text, and lets the user verify it.

## Solution

LegalLens is a web app where a layperson types a Query in English or Hindi and receives a plain-language answer grounded in Indian statute text. Every answer carries Citations that quote the original English Provision verbatim. Answers come from a Corpus of Provisions via Corrective RAG: retrieved Chunks are graded, and when the Corpus does not answer the Query, LegalLens rewrites the Query and uses a general web search Fallback, labelling the answer with a lower Trust label. Repealed Provisions are flagged with their Superseding provision. Out-of-scope queries are politely refused, a not-legal-advice disclaimer is always visible, and no accounts or chat history are stored. The project also ships an evaluation showing CRAG beats plain RAG, with an automated check that no Citation is hallucinated.

## User Stories

1. As a layperson, I want to type a legal question in plain English, so that I can understand my rights without legal training.
2. As a Hindi speaker, I want to ask my question in Hindi, so that I don't need English to get legal help.
3. As a Hindi speaker, I want the answer in Hindi, so that I can read and act on it comfortably.
4. As a Hindi speaker, I want the cited Provision text quoted in its original English, so that I can show the exact words to a lawyer or official.
5. As a user, I want every answer to cite the specific Act and Provision number it relies on, so that I can verify it myself.
6. As a user, I want each Citation to show the verbatim Provision text, so that I can read the law itself and not only a summary.
7. As a user, I want the answer written in plain language, so that I don't need to decode legal terminology.
8. As a user, I want the answer to state when the Corpus does not contain a reliable answer, so that I am not given a confident guess.
9. As a user, I want answers that came from the web Fallback to carry a visible Trust label, so that I know they are less reliable than statute-grounded answers.
10. As a user, I want Corpus-grounded answers to be labelled as such, so that I know they come from statute text.
11. As a user, I want to see which web sources supported a Fallback answer, so that I can judge them.
12. As a user asking about an offence, I want to be told when the Provision I asked about was repealed in July 2024, so that I don't rely on superseded law.
13. As a user who cites an old IPC section number, I want to be shown the Superseding provision in the BNS, so that I can find the current law.
14. As a user asking about a current offence in plain words, I want the answer to cite the in-force BNS Provision, and mention the old IPC equivalent where known, so that I can reconcile it with older sources.
15. As a user asking about criminal procedure or evidence, I want both BNSS/BSA and the old CrPC/IEA covered, so that I can understand the law whichever code my source mentions.
16. As a user asking about constitutional rights, I want answers citing Articles of the Constitution, so that I understand the basis of my rights.
17. As a tenant, I want to ask about tenancy law, so that I understand my position in a rent or eviction dispute.
18. As a consumer, I want to ask about consumer protection law, so that I know whether I have a complaint.
19. As a worker, I want to ask about labour law, so that I understand my entitlements.
20. As a user, I want the app to understand questions phrased informally ("my landlord won't return my deposit"), so that I don't need to know legal vocabulary.
21. As a user whose first retrieval is poor, I want the system to rewrite my Query and try again, so that I still get a useful answer.
22. As a user, I want a clear refusal when my Query is not about Indian law, so that I am not given an irrelevant or invented answer.
23. As a user asking "should I sue?" or "should I sign this?", I want the app to explain relevant law but decline to advise a personal course of action, so that I understand its limits.
24. As a user, I want a prominent not-legal-advice disclaimer on every page, so that I understand the tool is informational.
25. As a user, I want the refusal message to tell me why and suggest what I can ask instead, so that I can reformulate.
26. As a privacy-conscious user, I want no account and no stored chat history, so that my sensitive situation is not retained.
27. As a user, I want a fast, simple interface with one input box and a clear answer area, so that I can get help in seconds.
28. As a user on a phone, I want the interface to work on a small screen, so that I can use it anywhere.
29. As a user, I want a visible loading state while the answer is generated, so that I know the app is working.
30. As a user, I want a helpful error message when the service is unavailable or rate-limited, so that I know to retry.
31. As a user, I want my Query's language detected automatically, so that I don't have to pick a language setting.
32. As a user, I want to expand and collapse Citations, so that long Provision texts don't overwhelm the answer.
33. As a user, I want a Citation to show its Act, chapter and Status (in force or repealed), so that I can see how current it is.
34. As a developer, I want a one-command way to build the Corpus from source texts, so that the Corpus is reproducible.
35. As a developer, I want each Act parsed into one Chunk per Provision with Act, chapter, number and Status metadata, so that Citations map to exact retrievable units.
36. As a developer, I want the repealed-to-superseding Provision mapping stored with the Chunks, so that answers can point users to current law.
37. As a developer, I want the ingestion step to report Chunk counts per Act and flag suspicious counts, so that parsing mistakes are caught early.
38. As a developer, I want the Corpus built from open datasets and verified against India Code, so that the text is trustworthy.
39. As a developer, I want a plain-RAG baseline that retrieves and generates without grading, so that I can compare it with CRAG.
40. As a developer, I want a Grader that returns a Verdict of correct, ambiguous or incorrect, so that routing is explicit and testable.
41. As a developer, I want an incorrect Verdict to trigger query rewriting and the web Fallback, so that poor retrieval is corrected.
42. As a developer, I want an ambiguous Verdict to combine Corpus Chunks with Fallback results, so that partial answers are supplemented.
43. As a developer, I want a correct Verdict to generate from the Corpus Chunks only, so that grounded answers are not diluted by web content.
44. As a developer, I want the Fallback and Gemini to be replaceable behind interfaces, so that tests can fake them.
45. As a developer, I want an automated Hallucinated-citation check, so that any Citation not found in the Corpus is detected.
46. As a developer, I want an answer containing a Hallucinated citation to be blocked or regenerated, so that fake Provisions never reach users.
47. As a developer, I want a golden Q&A set with expected Provisions, so that retrieval and answers can be measured.
48. As a developer, I want the evaluation to report retrieval hit-rate, answer accuracy and citation validity for plain RAG and CRAG side by side, so that I can show CRAG's benefit.
49. As a developer, I want the golden set to include Hindi, repealed-code, out-of-scope and poor-retrieval cases, so that edge behaviour is measured.
50. As a developer, I want secrets such as API keys loaded from environment variables, so that none are committed.
51. As a recruiter or reviewer, I want a live deployed demo, so that I can try it without setup.
52. As a recruiter or reviewer, I want a README with an architecture diagram and evaluation results, so that I can understand the design and its quality quickly.
53. As a maintainer, I want a stateless backend, so that it can be deployed cheaply and scaled without session storage.
54. As an operator, I want the backend to degrade gracefully when the web search provider fails, so that the app answers from the Corpus or says it cannot answer.
55. As an operator, I want request limits to protect the Gemini free tier, so that the demo is not exhausted by abuse.

## Implementation Decisions

- **Product shape:** a stateless web app with a Python backend exposing one question-answering endpoint (and a health endpoint), and a Next.js frontend. No accounts, no stored chats.
- **Corpus:** statutes only. Constitution of India; IPC, CrPC, IEA; BNS, BNSS, BSA; and a set of consumer, tenancy and labour Acts (exact list to be settled during build). No case law; judgments reach users only through the Fallback.
- **Provision model:** each Provision is a Chunk with Act, chapter, number, text and Status (in force or repealed). Repealed Provisions carry a reference to their Superseding provision where known; in-force BNS/BNSS/BSA Provisions carry the old equivalent where known.
- **Ingestion module:** takes raw Act text (open datasets, verified and patched against India Code) and emits one Chunk per Provision. One parser per source format, behind a common interface. Reports per-Act counts and flags anomalies. See ADR 0002.
- **Retrieval module:** local vector store over Chunks using a local multilingual open-source embedding model, so Hindi Queries match English Provisions. Returns Chunks with metadata.
- **Language handling:** detect the Query language; Hindi Queries receive Hindi answers; Citations always quote the original English Provision verbatim.
- **Safety module:** classifies a Query as in scope or an Out-of-scope query (non-Indian-law, or requests for personal advice on whether to sue/sign/etc.) and returns a polite refusal with a suggested reformulation. The not-legal-advice disclaimer is always shown by the UI.
- **CRAG graph:** retrieve, then Grader returns a Verdict (correct, ambiguous, incorrect). Correct: generate from Chunks. Incorrect: rewrite Query, run the web Fallback, generate from Fallback results. Ambiguous: combine Chunks and Fallback results. See ADR 0001. Thresholds and the web search provider are settled during build.
- **Trust label:** every response carries whether support came from the Corpus, the Fallback, or both; Fallback sources are listed.
- **Citation verification module:** after generation, every Citation is checked against the Corpus; an answer with a Hallucinated citation is blocked or regenerated.
- **LLM:** Gemini for Grader, query rewriter and generator, behind an interface so tests can fake it. See ADR 0003. The web search provider is also behind an interface.
- **API contract:** the question endpoint accepts a Query and returns the answer text, answer language, Trust label, a list of Citations (Act, chapter, number, Status, verbatim text, Superseding provision if any), and Fallback sources if used. Refusals are a distinct response type with a reason.
- **Resilience:** Fallback failure degrades to Corpus-only or an explicit "cannot answer"; basic rate limiting protects the LLM free tier.
- **Plain RAG baseline:** a variant of the pipeline with no Grader and no Fallback, used only for evaluation comparison.
- **Frontend:** single page with a Query box, answer area, collapsible Citations, Trust label, repeal notices, loading and error states, mobile-friendly layout, persistent disclaimer.
- **Deployment:** hosted demo, frontend and backend deployed separately; targets chosen during build.
- **Configuration:** secrets via environment variables only.

## Testing Decisions

- **What makes a good test:** exercises external behaviour only (inputs and outputs at the seam), never internal prompts, graph node wiring or private helpers. Tests should survive refactoring the pipeline.
- **Seam 1: the question endpoint.** Query in, response out, with Gemini and the web search Fallback faked at the edge and a small fixture Corpus in a temporary vector store. Covers: correct/ambiguous/incorrect Verdict routing visible through Trust labels and sources; Hindi Query gets a Hindi answer with English Citation text; repealed-code Queries surface the Superseding provision; out-of-scope and personal-advice Queries are refused; a Hallucinated citation never reaches the response; Fallback failure degrades gracefully; the disclaimer-relevant response fields are present.
- **Seam 2: ingestion.** Raw Act text fixtures in, Chunks with metadata out, one fixture set per source format. Covers: correct Provision boundaries, numbering edge cases, Status and Superseding-provision metadata, per-Act count reporting and anomaly flags.
- **Evaluation (not a unit test seam):** a golden Q&A set run through the same endpoint seam against the real Corpus, comparing plain RAG and CRAG on retrieval hit-rate, answer accuracy and citation validity. Run on demand, reported in the README.
- **Frontend:** light checks that the disclaimer, Trust label and Citations render from a mocked API response; no end-to-end browser suite required for v1.
- **Prior art:** none yet; the existing health-check test is the first example of testing through the HTTP seam. Use the `tdd` skill for ingestion, Verdict routing and the citation verifier.

## Out of Scope

- Case law and court judgments as a Corpus.
- Accounts, authentication, chat history, saved conversations, follow-up questions within a session.
- Languages other than English and Hindi.
- Document upload or contract review.
- Legal advice, strategy, drafting, or lawyer referral.
- Official-domains-only Fallback or tiered trust ranking of web sources.
- Provider abstraction for multiple LLMs beyond what tests need.
- State-level laws and subordinate legislation (rules, notifications) unless within the chosen Acts.

## Further Notes

- Open items to settle during build: web search provider and Fallback thresholds; hosting targets and Gemini free-tier limits; exact consumer/tenancy/labour Act list.
- The Python version in the local venv (3.14) may lack wheels for the vector store and embedding dependencies; a downgrade to 3.12 may be needed.
- Domain vocabulary is defined in the project glossary; architectural rationale is in ADRs 0001–0003.
- Repo scaffolding (backend, frontend, health endpoint and test) already exists.
