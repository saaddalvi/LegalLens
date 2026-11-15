# 01: Supported Python and full backend install

**What to build:** A backend environment where every real dependency (vector store, local multilingual embeddings, LangGraph, Gemini client, FastAPI, test tooling) installs cleanly and the existing health test passes. If the current Python version lacks wheels for these dependencies, move to a supported version and document the choice.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] A fresh environment installs all backend dependencies with one documented command
- [x] The health test passes in that environment
- [x] The required Python version is recorded in the backend project metadata and the README
- [x] The embedding model loads and embeds one English and one Hindi sentence
