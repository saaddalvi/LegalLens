# Gemini for all generation, local multilingual embeddings for retrieval

The Grader, query rewriter and answer generator all use Gemini, to keep one provider and a free tier for a resume project. Embeddings come from a local open-source multilingual model (multilingual-e5 or BGE-M3) so Hindi Queries match English Provisions without a paid embedding API. Swapping the LLM later means re-tuning the Grader prompts and re-running evals.

## Note: bigger embedding models do not fix retrieval

`multilingual-e5-base` and `-large` scored 17 and 18 of 26 expected Provisions in the top 10, against 18 for `-small`, at up to 12 times the embedding time. Gemini embeddings were not measured: the free tier (30k tokens a minute, 1k requests a day) cannot embed the 3,501-Provision Corpus in a day. Retrieval was improved by splitting long Provisions instead (ADR 0002).

