    # Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Laypeople in India, writing in English or Hindi, facing a concrete situation: a question about their rights under Indian law, or a Contract (rent agreement, job offer, NDA) they don't understand. They are not lawyers and need plain explanations they can verify.

## Product Purpose

LegalLens answers questions about Indian law, grounded in statute text, with verifiable Citations. Users can also upload an English Contract to get a Contract brief (parties, purpose, key terms, obligations, Flagged clauses) and ask follow-up Queries in a Contract conversation. Success: a user understands their situation and can check every claim against the actual Provision or Clause.

## Positioning

Every answer is checked against the statute Corpus before it reaches the browser. A Hallucinated citation is regenerated once, then the answer is blocked. Each answer carries a Trust label saying whether support came from the Corpus, the web Fallback, the user's Contract, or nothing. It explains how a Clause differs from Indian law and never says whether to sign.

## Operating Context

Corrective RAG pipeline: scope check, retrieval (Chroma + Qwen3 embeddings), Grader Verdict, Tavily Fallback, generation, Citation check. Stages are shown to the user while they wait. Answers stream over SSE. Frontend is Next.js on Vercel with Clerk auth; backend is FastAPI on a Hugging Face Space. Users have a daily cap on new Contracts and Queries. Domain vocabulary lives in `GLOSSARY.md` and decisions in `docs/adr/`.

## Capabilities and Constraints

- Corpus covers Acts such as the Bharatiya Nyaya Sanhita and the Constitution; each Provision has a Status (in force, repealed, model).
- Only English Contracts are accepted; scanned Contracts are supported.
- Use glossary terms in UI copy: Provision (not clause/rule), Clause (Contract only), Citation (to a Provision), Clause reference (to a Contract), Flagged clause (never "red flag" or "risky"), Query, Contract brief.
- LegalLens is for information only and is not legal advice. It refuses personal-advice Queries (whether to sue or sign) as Out-of-scope queries. A Query asking what one can do is answered with the law and the remedies, never which to choose.
- Devanagari must render and read well in Queries and answers.

## Evidence on Hand

Real Corpus text, ADRs, and fixture Contracts under `backend/fixtures/contracts/`. No testimonials, usage numbers, or customer proof exist; the demo is not yet deployed. Future work must not fabricate any of these.

## Product Principles

1. Verifiability over fluency: every claim points to a Citation or Clause reference the user can read verbatim.
2. Say how, never whether: describe how a Clause differs from the law; never advise a decision.
3. Show the work: Stages, Trust labels and refusals are visible, not hidden.
4. Plain language for laypeople, in their language, without dropping legal precision.

## Accessibility & Inclusion

Hindi (Devanagari) support is required alongside English. Every answer carries the not-legal-advice disclaimer.
