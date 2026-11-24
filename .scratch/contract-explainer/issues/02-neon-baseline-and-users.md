# 02: Neon, SQLAlchemy and Alembic baseline with users

**What to build:** The backend gets a Postgres database on Neon, accessed with SQLAlchemy 2 (async) and psycopg, with Alembic migrations in the backend package and the pgvector extension enabled (see `../spec.md`, "Persistence" and "Users"). The first migration creates `users`. A `users` row is created the first time a signed-in request arrives. `POST /webhooks/clerk` verifies Clerk's Svix signature and, on `user.deleted`, deletes that user's row. Later tables cascade from it. `/ask` keeps working with no database configured, as ADR 0005 requires.

**Blocked by:** 01 (Clerk sign-in)

**Status:** done

- [x] `alembic upgrade head` on an empty database creates `users` and enables `vector`
- [x] Endpoint test: the first signed-in request creates exactly one `users` row, and later requests don't duplicate it
- [x] Endpoint tests: a webhook with a bad or missing signature gets 400 and changes nothing. A valid `user.deleted` removes the row
- [x] `/ask` works with `DATABASE_URL` unset
- [x] Tests run against a test Postgres with pgvector (a local Postgres or a Neon branch, documented in the README)
- [x] The deploy notes say to run migrations before starting the Space, and list `DATABASE_URL` and the Clerk webhook secret as Space secrets
- [x] Lint and tests pass
