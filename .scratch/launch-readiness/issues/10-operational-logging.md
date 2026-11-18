# 10: Operational logging

**What to build:** Once the app is live, show where time and Gemini quota go without rerunning the evaluation: one structured log line per request.

**Status:** done

- [x] One JSON record per request on `/ask` and `/ask/stream`: endpoint, outcome (`answer`, `error`, `client_gone`), language, Query length, cache hit, total time, time per Stage, response type and Trust label
- [x] The pipeline fills an optional `trace` with the Grader's score and Verdict, the Fallback's source count, whether the Citation check forced a rewrite (`citation_recheck`) and whether it blocked the answer (`citation_blocked`); a blocked answer also logs a warning
- [x] A failed request records the Stage that was running (`error_stage`)
- [x] A Stage lasts until the next starts, and one that runs twice (generation after a rewrite) adds up
- [x] The Query and the answer are never logged, only the Query's length and language. Tested with a Query containing a name, in English and Hindi, and the test first checks a record was written, so it cannot pass on an empty log
- [x] The line reaches the console under uvicorn (Python drops INFO logs without a handler, so the module adds one when nothing else is configured). Checked on a real server: one record per request, no duplicates, no Query text
- [x] README: a Logs section

## Notes

- `/ask` now passes the same stage callback as `/ask/stream`, only to time Stages. The answer and the evaluation harness are unaffected: `legallens.evaluate` builds its own app and its answers are scored as before.
- Exception tracebacks written by the existing `logging.exception` calls are not covered by the privacy rule: if a provider's error message echoed a Query, it would be in the log. None did in the cases tried (missing key), but it is not guaranteed.
- Counting Citation blocks or Fallback rates is left to whoever reads the logs (a `grep`/`jq` over the lines); there is no metrics endpoint.
