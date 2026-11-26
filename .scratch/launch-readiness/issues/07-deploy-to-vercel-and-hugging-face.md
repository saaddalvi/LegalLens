# 07: Deploy to Vercel and a Hugging Face Space

**What to build:** Everything needed to put the demo live: a backend image, a way to ship the gitignored Corpus with it, a wizard for the steps only the owner can do, and the README's deploy section and architecture diagram. Closes the code side of v1 ticket 12.

**Blocked by:** 02, 04, 05

**Status:** ready-for-human (the live deploy needs the owner's Hugging Face and Vercel accounts)

- [x] `backend/Dockerfile`: CPU-only torch, versions pinned by `backend/constraints.txt`, the embedding model baked in, runs as user 1000, `--proxy-headers`, `REQUIRE_CORPUS=1` and `WARM_START=1`
- [x] `backend/.dockerignore` keeps `.env` and other bulk out of the image
- [x] `backend/scripts/deploy_space.py` assembles the Space's files around the gitignored Corpus, refuses an empty or sample-only Corpus, and uploads only when given `--push`
- [x] `scripts/deploy-wizard.sh` walks through the owner-only steps and ends with a live `/ready` and CORS check
- [x] README: architecture diagram, settings table, Deploy section
- [x] The staged copy was started with the container's environment: `/ready` reported 3,501 Provisions and `fixture: false`, the embedding model loaded before startup completed, the 6th `/ask` in a minute got 429, and a forwarded client address was counted separately
- [x] `docker build` and `docker run`, verified 2026-11-26: the staged Space files built for `linux/amd64` (emulated on an arm64 Mac) and the migrations ran from inside the image. With fake API keys and a temporary Postgres, `/ready` reported 3,693 Provisions and `fixture: false`, a Corpus search worked offline, unsigned `/ask` and `/contracts` got 401, the Clerk webhook got 400 unsigned and 200 signed, and CORS allowed only the configured origin. Not covered: a real Query or Contract upload, and the README's native build from `backend/`
- [ ] Run `scripts/deploy-wizard.sh`; the owner confirms the deployed site works, then the demo link goes in the README
- [ ] Checked by hand in a browser (including ticket 06's button) at phone width and in both colour schemes

## Notes

- The notes that planned this said "push to the Space with git-lfs". `git-lfs` is not installed, and `huggingface_hub.upload_folder` (already a dependency of sentence-transformers) handles large files by itself, so the script uses that.
- The Space must be public so the browser can reach it. It holds the code and the Corpus, not keys.
- The free Space sleeps when idle; the first request after that is slow.
- `docker run --env-file` keeps quotes as part of a value, so a quoted `DATABASE_URL` in `backend/.env` makes the container exit with `Could not parse SQLAlchemy URL` (reproduced with a fake value, 2026-11-26). Remove the quotes for a local container run. In the Space's settings, paste values without quotes.
- 2026-11-26: the wizard now also covers the Clerk keys and webhook, the Neon database and the migrations. It was rehearsed with the upload, `git`, browser and network calls stubbed, and has not been run against the real accounts.
