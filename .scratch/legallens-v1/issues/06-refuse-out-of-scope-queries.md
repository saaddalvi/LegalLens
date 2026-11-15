# 06: Refuse out-of-scope queries

**What to build:** Queries that are not about Indian law, or that ask for personal advice such as whether to sue or sign, receive a polite refusal with the reason and a suggested reformulation. Relevant law can still be explained without advising a course of action.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Endpoint tests: a non-Indian-law Query returns a refusal response type with a reason
- [ ] Endpoint tests: "should I sue/sign" Queries return a refusal or a law-only explanation with no personal recommendation
- [ ] Endpoint test: ordinary in-scope Queries are not refused
- [ ] The frontend shows refusals distinctly with the suggested reformulation
- [ ] The disclaimer remains visible on every state of the page
