# 07: Delete a Contract and daily caps

**What to build:** Users can delete a Contract, and per-user daily caps protect the Gemini quota (see `../spec.md`, "Deletion" and "Rate limiting per user"). `DELETE /contracts/{id}` removes the Contract and, by cascade, its Clauses, vectors and Contract conversation. The list and the Contract page offer Delete with a confirmation. A `usage` table counts new Contracts and Contract-conversation Queries per user per day (UTC). Defaults are 5 and 50, set by environment variables, with 0 turning a cap off. Over the cap, the endpoint answers 429 with `Retry-After` before any work or stream starts. Refused uploads don't count.

**Blocked by:** 06 (Contract conversation)

**Status:** ready-for-agent

- [ ] Endpoint test: deleting a Contract removes its rows from every table. Deleting another user's Contract gets 404
- [ ] Endpoint test: the Clerk `user.deleted` webhook removes the user's Contracts, Clauses and messages
- [ ] Endpoint tests: the 6th Contract and the 51st Query in a day get 429 with `Retry-After`. A refused upload doesn't consume the cap. The count resets the next day
- [ ] Component tests: Delete asks for confirmation and removes the Contract from the list, and the 429 message says when the limit resets
- [ ] Lint, typecheck and tests pass
