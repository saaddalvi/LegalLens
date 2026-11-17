from typing import Protocol

MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"


class Embedder(Protocol):
    def embed(self, texts: list[str], *, is_query: bool) -> list[list[float]]: ...


class LocalEmbedder:
    """Local multilingual embeddings (ADR 0003). Model loads on first use.

    Qwen3-Embedding expects an instruction in front of each Query and nothing in front of a
    Provision; the model ships it as the `query` prompt."""

    def __init__(self, model_name: str = MODEL_NAME, model=None):
        self._model_name = model_name
        self._model = model

    def embed(self, texts: list[str], *, is_query: bool) -> list[list[float]]:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        kwargs = {"prompt_name": "query"} if is_query else {}
        vecs = self._model.encode(texts, normalize_embeddings=True, **kwargs)
        return vecs.tolist()
