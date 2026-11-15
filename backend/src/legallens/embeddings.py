from typing import Protocol

MODEL_NAME = "intfloat/multilingual-e5-small"


class Embedder(Protocol):
    def embed(self, texts: list[str], *, is_query: bool) -> list[list[float]]: ...


class E5Embedder:
    """Local multilingual embeddings (ADR 0003). Model loads on first use."""

    def __init__(self, model_name: str = MODEL_NAME):
        self._model_name = model_name
        self._model = None

    def embed(self, texts: list[str], *, is_query: bool) -> list[list[float]]:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        prefix = "query: " if is_query else "passage: "
        vecs = self._model.encode([prefix + t for t in texts], normalize_embeddings=True)
        return vecs.tolist()
