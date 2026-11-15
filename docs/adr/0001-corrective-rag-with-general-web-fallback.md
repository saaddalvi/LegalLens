# Corrective RAG with a general web search Fallback

LegalLens grades retrieved Chunks and, when the Verdict is poor, rewrites the Query and falls back to a general web search API, as in the original CRAG design. We rejected an official-domains-only Fallback for broader recall, and accept the lower trust by always showing a Trust label on Fallback-sourced answers.
