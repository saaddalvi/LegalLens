# 08: Harden the web Fallback

**What to build:** Prefer official sources in the web Fallback, and stop web text from being able to act as instructions to the generation model.

**Status:** done

- [x] The Fallback searches `gov.in`, `nic.in`, `prsindia.org` and `indiankanoon.org` first, and the open web once only when those return nothing
- [x] A bare domain covers its subdomains. Checked against the live API (the docs are silent): the restricted search for the RTI application fee returned `rti.sci.gov.in`, `rtionline.gov.in` and state `gov.in` sites, where the open search returned a YouTube video and a Facebook post among its first five
- [x] Snippets are cut to 1,000 characters
- [x] Each web source reaches the generation prompt fenced in `<web_source>` tags with `<`, `>` and quotes escaped, and the prompt says the text is untrusted and its instructions are to be ignored
- [x] Tests, with an `httpx.MockTransport` and no network: official search first, one open retry only when empty, no open search when official sources answer, snippet cut, errors raised for the pipeline to handle; a snippet that tries to close its fence cannot
- [x] ADR 0004 amended (it said "one HTTP call"; ADR 0001's rejection of an official-only Fallback is respected, since the open web is still the second try)
- [x] Rerun `python -m legallens.evaluate` and refresh the README results (2026-11-18, `gemini-3.1-flash-lite`, same model as the previous run). Poor-retrieval CRAG stayed at 80%, but two Fallback-path cases flipped (`poor-rti` now right, `poor-drunk-driving` now wrong) and English CRAG fell to 93% on `en-ir-strike`, also a Fallback case. See the README.

## Notes

- Wildcards (`*.gov.in`) are not documented by Tavily, so none are used.
- Tavily also has an `include_domains_mode` parameter. Whether a "prefer" mode exists for Search was not confirmed, so the two-search design is used; it works under either mode.
- `indiankanoon.org` hosts case law and user-posted text. It is in the list because Indian Kanoon is where the IPC text came from, but it is the least official entry.
