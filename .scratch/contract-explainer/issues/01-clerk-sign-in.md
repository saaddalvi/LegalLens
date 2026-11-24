# 01: Clerk sign-in across the app

**What to build:** Users sign in with Clerk before using `/ask`. The landing page and `/law` stay public (see `../spec.md`, "Sign-in boundary" and "Rate limiting per user"). Clerk's Next.js middleware protects `/ask` and `/contracts/**`, and the header gets sign-in and user buttons. The frontend sends the Clerk session token as a bearer token on every backend call. FastAPI verifies the token against Clerk's JWKS (issuer and authorised party) and gets the Clerk user id. `/ask` and `/ask/stream` require it. `/health`, `/ready` and the `/law` data endpoints don't. The existing `RateLimiter` is keyed by user id instead of client address. `/ask`'s answers, Stages and cache are otherwise unchanged.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] Endpoint tests: `/ask` and `/ask/stream` without a token, or with an invalid or expired one, get 401 before any work starts
- [x] Endpoint tests: `/health`, `/ready` and the `/law` data endpoints need no token
- [x] Endpoint test: rate limits are counted per user id, so two users from one address are counted separately
- [x] The token verifier is injected through `create_app` (a fake that accepts test tokens in tests). Existing `/ask` and evaluation tests pass with it
- [x] Frontend: signed-out visits to `/ask` redirect to sign-in. `/` and `/law/**` render signed out. The landing page's ask box and example Queries go through sign-in and then land on `/ask?q=…`
- [x] README settings table lists the Clerk variables for the backend and frontend
- [x] Lint, typecheck and tests pass
