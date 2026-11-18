# 12: Deploy, rate limiting and README

**What to build:** A live public demo with request limits that protect the Gemini free tier, and a README that lets a reviewer understand the project in minutes.

**Blocked by:** 10, 11

**Status:** in progress. Everything that can be done without the owner's Hugging Face and Vercel accounts is done (see `../../launch-readiness/issues/`); the live deploy and the demo link are open.

- [ ] Frontend and backend are deployed to chosen hosts (open item from the spec) and the demo works end to end. Hosts chosen: Vercel (frontend) and a Hugging Face Docker Space (backend). Run `scripts/deploy-wizard.sh`.
- [x] Endpoint test: requests beyond the limit receive a clear rate-limit response (launch-readiness 02; also checked against a running server: the 6th request in a minute gets 429)
- [ ] Secrets are configured through the hosts' environment settings, none committed (nothing is committed or baked into the image; the wizard walks through setting them)
- [ ] The README has an architecture diagram, setup instructions, the evaluation results and a link to the demo (all there except the link, which needs the deploy)
- [ ] The not-legal-advice disclaimer is visible in the deployed app (it is on `/` and `/ask`; confirm on the deployed site)
