# Gemini for all generation, local multilingual embeddings for retrieval

The Grader, query rewriter and answer generator all use Gemini, to keep one provider and a free tier for a resume project. Embeddings come from a local open-source multilingual model (multilingual-e5 or BGE-M3) so Hindi Queries match English Provisions without a paid embedding API. Swapping the LLM later means re-tuning the Grader prompts and re-running evals.
