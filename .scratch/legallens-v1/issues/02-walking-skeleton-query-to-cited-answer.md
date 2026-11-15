# 02: Walking skeleton, Query to cited answer

**What to build:** A user types a Query on the web page and sees an answer with Citations. The question endpoint retrieves from a small fixture Corpus in a vector store, generates through a Gemini interface, and returns the answer plus Citations (Act, number, Status, verbatim text). The page shows the answer, the Citations and an always-visible not-legal-advice disclaimer. The Gemini and web-Fallback interfaces exist from the start, with fakes for tests.

**Blocked by:** 01

**Status:** done

- [x] Tests at the endpoint seam, with Gemini faked and a temporary fixture Corpus: a Query returns an answer with at least one Citation whose text matches the fixture Provision verbatim
- [x] The response contract includes answer text, answer language, Trust label, Citations and Fallback sources (the last two may be empty)
- [x] The frontend renders the answer, Citations and the disclaimer from a live backend response
- [x] Secrets are read from environment variables only
- [x] The app runs locally end to end with one documented command per side
