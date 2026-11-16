# 13: Distinct Status for model Acts

**What to build:** A Provision from a template Act such as the Model Tenancy Act is shown and described as "not in force by itself", not as in force, so a user does not take a State template for binding law. The Status gains a value for this, and the Citation, the generated answer and the page all carry it.

**Blocked by:** 09

**Status:** ready-for-agent

Context: ticket 09 added the Model Tenancy Act 2021 for rental-deposit Queries. `Status` (`backend/src/legallens/models.py`) only allows `in_force` and `repealed`, so its Chunks are stored as `in_force` under the Act name "Model Tenancy Act" (`EVERYDAY_ACTS["mta"]` in `backend/src/legallens/ingestion/everyday_acts.py`). `backend/sources/everyday_acts.json` records this as a workaround.

Decide first (grill the user): the value's name and wording (for example `model`, or a broader "not in force by itself"), and whether an answer citing it must add an explicit caution that the user's State may differ.

- [ ] GLOSSARY.md's **Status** entry covers the new value
- [ ] `Status` has the new value and the Model Tenancy Act's Chunks use it; the Corpus builds with no warnings
- [ ] The LLM prompt (`backend/src/legallens/llm.py`, which already special-cases "repealed") tells the model to say a model-Act Provision is a template and to point the user to their State's own law
- [ ] Endpoint test: a rental-deposit Query returns a Citation with the new Status, and the fake LLM receives it
- [ ] The frontend shows the new Status on a Citation (the same place as in force and repealed), with a test in ticket 10's style
- [ ] `sources/everyday_acts.json` and ticket 09's notes no longer call the Status a workaround
