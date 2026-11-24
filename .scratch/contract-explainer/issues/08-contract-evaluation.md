# 08: Evaluate Contract answering with sample Contracts

**What to build:** The evaluation measures Contract answering the way it measures `/ask` (see `../spec.md`, "Testing Decisions", Evaluation). Add three sample Contracts written for testing to the backend fixtures: a rent agreement with a deposit over the Model Tenancy Act's limit, a job offer with a post-employment non-compete, and an NDA. Each has expected Flagged clauses (Clause number and the Provision cited) and follow-up cases:
- one Clause-supported answer
- one Contract-silent answer
- one law question
- one "should I sign?" refusal
- one Hindi Query

The harness drives the Contract endpoints through the app, as it drives `/ask`, and reports flag recall and precision, Clause-reference correctness and follow-up accuracy in `evaluation/report.md` and the README results.

**Blocked by:** 03 (Indian Contract Act), 06 (Contract conversation)

**Status:** done

- [x] The three sample Contracts and their expected cases are checked in, with no real personal data
- [x] The evaluation runs the Contract cases with `--contracts` (or similar), and the existing `/ask` evaluation is unchanged
- [x] The report lists, per Contract: expected against found flags, Hallucinated clause references (expected 0) and the follow-up results
- [x] A first run is recorded in the README results with the model name and date
