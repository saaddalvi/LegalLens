# LegalLens backend, for a Hugging Face Docker Space (it also runs anywhere else Docker does).
#
# The build context is `backend/` with a built Corpus at `data/chroma/` (gitignored, so it
# is not in a fresh clone; see `scripts/deploy_space.py`, which assembles the same layout).
# Secrets are never baked in: pass GOOGLE_API_KEY and WEB_SEARCH_API_KEY at run time.
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf

WORKDIR /app

# Layers are ordered so that a code change reuses the slow ones (torch, the 1.1 GB model).

# CPU-only torch: the default wheel bundles CUDA libraries the Space has no use for.
COPY constraints.txt pyproject.toml ./
RUN pip install --index-url https://download.pytorch.org/whl/cpu -c constraints.txt torch

# The rest of the dependencies, read from pyproject.toml so they are listed once.
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))" > requirements.txt \
    && pip install -c constraints.txt -r requirements.txt

# The embedding model is downloaded now, so the running container never needs the network for it.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('Qwen/Qwen3-Embedding-0.6B')" \
    && chmod -R a+rX /opt/hf

# Hugging Face Spaces run the container as user 1000.
RUN useradd -m -u 1000 user
USER user
WORKDIR /home/user/app

COPY --chown=user:user src ./src
COPY --chown=user:user fixtures ./fixtures
# Chroma writes next to the store even when only reading, so the user must own it.
COPY --chown=user:user data/chroma ./data/chroma

ENV PYTHONPATH=/home/user/app/src \
    CHROMA_PATH=/home/user/app/data/chroma \
    HF_HUB_OFFLINE=1 \
    REQUIRE_CORPUS=1 \
    WARM_START=1

EXPOSE 7860
# --proxy-headers makes the client address the real one behind the Space's proxy, which the
# rate limit counts by.
CMD ["uvicorn", "legallens.main:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers", "--forwarded-allow-ips", "*"]
