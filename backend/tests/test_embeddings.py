"""The local embedder gives Queries the model's instruction prompt and Provisions none."""

import numpy as np

from legallens.embeddings import MODEL_NAME, LocalEmbedder


class StubModel:
    def __init__(self):
        self.calls = []

    def encode(self, texts, **kwargs):
        self.calls.append((list(texts), kwargs))
        return np.ones((len(texts), 3))


def test_queries_use_the_query_prompt_and_provisions_use_none():
    model = StubModel()
    embedder = LocalEmbedder(model=model)
    embedder.embed(["what is theft"], is_query=True)
    embedder.embed(["Section 303 ..."], is_query=False)
    (qtexts, qkw), (ptexts, pkw) = model.calls
    assert qkw["prompt_name"] == "query" and qtexts == ["what is theft"]
    assert "prompt_name" not in pkw and ptexts == ["Section 303 ..."]
    assert qkw["normalize_embeddings"] and pkw["normalize_embeddings"]


def test_the_default_model_is_qwen3():
    assert MODEL_NAME == "Qwen/Qwen3-Embedding-0.6B"
