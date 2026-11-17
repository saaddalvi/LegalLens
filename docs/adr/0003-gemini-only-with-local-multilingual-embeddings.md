# Gemini for all generation, local multilingual embeddings for retrieval

The Grader, query rewriter and answer generator all use Gemini, to keep one provider and a free tier for a resume project. Embeddings come from a local open-source multilingual model (now Qwen3-Embedding-0.6B; see the last note) so Hindi Queries match English Provisions without a paid embedding API. Swapping the LLM later means re-tuning the Grader prompts and re-running evals.

## Note: bigger e5 models do not fix retrieval

`multilingual-e5-base` and `-large` scored 17 and 18 of 26 expected Provisions in the top 10, against 18 for `-small`, at up to 12 times the embedding time. Gemini embeddings were not measured: the free tier (30k tokens a minute, 1k requests a day) cannot embed the 3,501-Provision Corpus in a day. Retrieval was improved by splitting long Provisions instead (ADR 0002).


## Note: long-input models (ticket 16)

Measured with `backend/scripts/compare_embeddings.py` on the same 26 retrieval cases (hit = expected Provision in the top 10), embedding the 3,501 Provisions on an Apple-silicon laptop (MPS). Qwen3 queries use the model's built-in `query` instruction prompt (supported by `sentence-transformers` 6.3.0); neither model needs `trust_remote_code`.

| Model | Input | Hits | Embed time | Weights on disk |
|---|---|---|---|---|
| multilingual-e5-small (current) | 800-char pieces | 20 | 24 s | 449 MB |
| bge-m3 | 800-char pieces | 22 | 265 s | ~2.2 GB |
| bge-m3 | whole Provisions (8192 tokens) | 22 | 373 s | ~2.2 GB |
| Qwen3-Embedding-0.6B | 800-char pieces | 23 | 189 s | 1.1 GB (bf16) |
| Qwen3-Embedding-0.6B | whole Provisions (8192 tokens) | 23 | 301 s | 1.1 GB (bf16) |

The three named gaps (rank of the expected Provision; e5-small pieces: 25, 17, 13):

| Gap | bge-m3 pieces | bge-m3 whole | Qwen3 pieces | Qwen3 whole |
|---|---|---|---|---|
| FIR (BNSS 173) | 1 | 1 | 1 | 3 |
| Electronic evidence (BSA 63) | 22 (miss) | 40 (miss) | 2 | 5 |
| Hindi wages | 4 | 1 | 3 | 10 |

Qwen3 fixes all three but loses Hindi tenancy deposit (`hi-mta-deposit`, rank 32 pieces / 14 whole; it was rank 2). Both models still miss the repealed-code cases that depend on naming a section (IPC 302, IEA 65B), which no embedding fixes. Splitting into pieces made no difference to the hit count for either model, so whole-Provision input is not worth its extra time.

## Decision: Qwen3-Embedding-0.6B on 800-character pieces

Adopted (ticket 16). It scores 23 of 26 against 20, fixes the three named gaps and is smaller and faster than bge-m3. The cost is about 8 times the embedding time of e5-small (the Corpus build took about 4 minutes) and 1.1 GB of weights instead of 449 MB, plus the load at startup in the deployed app. Queries use the model's `query` instruction prompt; Provisions get none (`LocalEmbedder`, tested in `tests/test_embeddings.py`). Hindi tenancy deposit regressed (rank 2 to 32). Retrieval through the real Corpus reproduced 23 of 26, and the full evaluation was rerun (README).
