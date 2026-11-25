"""Evaluation of Contract answering: sample Contracts uploaded through the app, then asked about.

Each sample Contract (written for testing, with no real personal data) lists the Flagged clauses
a good brief should find and one follow-up Query of each kind: a Clause-supported answer, a
Contract-silent answer, a law question, a "should I sign?" refusal and a Hindi Query. The harness
drives `POST /contracts/stream` and `POST /contracts/{id}/ask/stream` through the app, as the
`/ask` evaluation drives `/ask`, and scores:

- flag recall and precision: an expected flag is found when the brief flags that Clause (or a
  sub-Clause or parent of it) and cites one of the expected Provisions;
- Clause-reference correctness: every Clause reference in the brief and in the answers must name
  a stored Clause, and quote its text verbatim (Hallucinated clause references, expected 0);
- follow-up accuracy, judged by the kind of Query.

Run it with `python -m legallens.evaluate --contracts`.
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel

from .evaluation import GoldenCase, Judge, _pct, _ratio, _with_retries
from .llm import ProvisionRef
from .models import AskResponse, ClauseOut, ClauseReference, ContractAnswer

log = logging.getLogger(__name__)

FollowUpKind = Literal[
    "clause_supported", "contract_silent", "law", "sign_refusal", "hindi"
]
SECTION_TITLE = "## Contract evaluation"
SECTION_END = "<!-- end contract evaluation -->"


class ExpectedFlag(BaseModel):
    clause: str
    # The brief must cite at least one of these Provisions for the Clause.
    provisions: list[ProvisionRef]


class FollowUp(BaseModel):
    kind: FollowUpKind
    query: str
    # Key points a correct answer states, for the judge. Not used for a refusal.
    reference: str = ""
    # clause_supported and hindi: the answer must quote at least one of these Clauses.
    expected_clauses: list[str] = []
    # law: the answer must cite at least one of these Provisions.
    expected_provisions: list[ProvisionRef] = []


class SampleContract(BaseModel):
    id: str
    title: str
    text: str
    expected_flags: list[ExpectedFlag]
    followups: list[FollowUp]


def load_samples(path: Path) -> list[SampleContract]:
    """The sample Contracts of a `cases.json`, each with its `text_file` read from beside it."""
    out = []
    for raw in json.loads(path.read_text()):
        text = (path.parent / raw.pop("text_file")).read_text()
        out.append(SampleContract(text=text, **raw))
    return out


class FoundFlag(BaseModel):
    clause: str
    provisions: list[str]  # "Act number"


class FollowUpOutcome(BaseModel):
    kind: FollowUpKind
    query: str
    accurate: bool = False
    error: str | None = None  # set when it could not be scored; left out of the metrics
    response_type: str = "-"
    trust_label: str = "-"
    answer_language: str = "-"
    clause_references: int = 0
    unverified_clause_references: int = 0


class ContractOutcome(BaseModel):
    id: str
    title: str
    error: str | None = None  # set when the Contract could not be uploaded
    expected_flags: list[str] = []  # "clause: Act number"
    found_flags: list[FoundFlag] = []
    expected_found: int = 0  # expected flags the brief found
    found_correct: int = 0  # found flags that match an expected one
    clause_references_checked: int = 0
    unverified_clause_references: int = 0
    followups: list[FollowUpOutcome] = []


class ContractEvaluation(BaseModel):
    contracts: list[ContractOutcome]

    def _scored(self) -> list[ContractOutcome]:
        return [c for c in self.contracts if c.error is None]

    @property
    def flag_recall(self) -> float | None:
        total = sum(len(c.expected_flags) for c in self._scored())
        return sum(c.expected_found for c in self._scored()) / total if total else None

    @property
    def flag_precision(self) -> float | None:
        total = sum(len(c.found_flags) for c in self._scored())
        return sum(c.found_correct for c in self._scored()) / total if total else None

    @property
    def clause_references_checked(self) -> int:
        return sum(
            c.clause_references_checked
            + sum(f.clause_references for f in c.followups if f.error is None)
            for c in self._scored()
        )

    @property
    def hallucinated_clause_references(self) -> int:
        return sum(
            c.unverified_clause_references
            + sum(
                f.unverified_clause_references for f in c.followups if f.error is None
            )
            for c in self._scored()
        )

    def _followups(self) -> list[FollowUpOutcome]:
        return [f for c in self._scored() for f in c.followups if f.error is None]

    @property
    def followup_accuracy(self) -> float | None:
        return _ratio([f.accurate for f in self._followups()])

    @property
    def followup_accuracy_by_kind(self) -> dict[str, float | None]:
        grouped: dict[str, list[bool]] = defaultdict(list)
        for f in self._followups():
            grouped[f.kind].append(f.accurate)
        return {k: _ratio(v) for k, v in grouped.items()}


class _Client(Protocol):
    """The slice of a test or HTTP client this harness uses (a signed-in `TestClient`)."""

    def post(self, url: str, **kwargs): ...
    def get(self, url: str, **kwargs): ...
    def delete(self, url: str, **kwargs): ...


# --- scoring --------------------------------------------------------------------------------


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def unverified_clause_references(
    refs: list[ClauseReference], stored: list[ClauseOut]
) -> list[ClauseReference]:
    """The references that name no stored Clause, or quote text that is not that Clause's."""
    by_number = {c.number: _norm(c.text) for c in stored}
    return [
        r
        for r in refs
        if r.number not in by_number or _norm(r.text) != by_number[r.number]
    ]


def _related(a: str, b: str) -> bool:
    """The same Clause, or one inside the other (7.2 in 7, 7(a) in 7)."""
    return a == b or any(
        x.startswith(y + sep) for x, y in ((a, b), (b, a)) for sep in (".", "(")
    )


def _provision_key(act: str, number: str) -> str:
    return f"{act} {number}"


def _flag_scores(
    expected: list[ExpectedFlag], found: list[FoundFlag]
) -> tuple[int, int]:
    def matches(e: ExpectedFlag, f: FoundFlag) -> bool:
        wanted = {_provision_key(p.act, p.number) for p in e.provisions}
        return _related(e.clause, f.clause) and bool(wanted & set(f.provisions))

    return (
        sum(any(matches(e, f) for f in found) for e in expected),
        sum(any(matches(e, f) for e in expected) for f in found),
    )


def _followup_accurate(
    case: FollowUp, response: ContractAnswer, judge: Judge, sample_id: str
) -> bool:
    if case.kind == "sign_refusal":
        return response.response_type == "refusal"
    if response.response_type == "refusal":
        return False
    quoted = {r.number for r in response.clause_references}
    if case.expected_clauses and not any(
        _related(q, e) for q in quoted for e in case.expected_clauses
    ):
        return False
    if case.expected_provisions:
        cited = {_provision_key(c.act, c.number) for c in response.citations}
        if not cited & {
            _provision_key(p.act, p.number) for p in case.expected_provisions
        }:
            return False
    if case.kind == "hindi" and response.answer_language != "hi":
        return False
    golden = GoldenCase(
        id=f"{sample_id}-{case.kind}",
        category="hindi" if case.kind == "hindi" else "english",
        query=case.query,
        reference=case.reference,
    )
    return _with_retries(lambda: judge.is_accurate(golden, _as_ask(response)))


def _as_ask(response: ContractAnswer) -> AskResponse:
    return AskResponse(**response.model_dump(include=set(AskResponse.model_fields)))


# --- driving the app ------------------------------------------------------------------------


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for frame in text.strip().split("\n\n"):
        if not frame or frame.startswith(":"):
            continue
        lines = dict(line.split(": ", 1) for line in frame.split("\n") if ": " in line)
        if "event" not in lines or "data" not in lines:
            continue
        try:
            events.append((lines["event"], json.loads(lines["data"])))
        except ValueError:
            continue
    return events


class _StreamFailed(Exception):
    """A stream ended in `error` or without an answer: transient, so it is retried."""


def _final_event(response, *, want: str) -> dict:
    if response.status_code != 200:
        raise _StreamFailed(f"HTTP {response.status_code}")
    events = _parse_sse(response.text)
    name, data = events[-1] if events else ("none", {})
    if name != want:
        raise _StreamFailed(f"stream ended in {name}")
    return data


def _upload(client: _Client, sample: SampleContract, sleep) -> dict:
    return _with_retries(
        lambda: _final_event(
            client.post("/contracts/stream", data={"text": sample.text}),
            want="answer",
        ),
        sleep=sleep,
    )


def _ask(client: _Client, contract_id: str, query: str, sleep) -> ContractAnswer:
    """Asks with no `conversation_id`, so each case starts a Contract conversation of its own
    and none sees another's turns."""
    data = _with_retries(
        lambda: _final_event(
            client.post(f"/contracts/{contract_id}/ask/stream", json={"query": query}),
            want="answer",
        ),
        sleep=sleep,
    )
    return ContractAnswer(**data)


def _evaluate_contract(
    sample: SampleContract, client: _Client, judge: Judge, sleep
) -> ContractOutcome:
    expected_labels = [
        f"{f.clause}: "
        + " or ".join(_provision_key(p.act, p.number) for p in f.provisions)
        for f in sample.expected_flags
    ]
    outcome = ContractOutcome(
        id=sample.id, title=sample.title, expected_flags=expected_labels
    )
    try:
        try:
            uploaded = _upload(client, sample, sleep)
            _score_contract(outcome, sample, uploaded, client, judge, sleep)
        except Exception as exc:
            log.exception("contract %s could not be scored", sample.id)
            # Nothing partial is kept: a half-scored Contract would skew the totals.
            outcome = ContractOutcome(
                id=sample.id,
                title=sample.title,
                expected_flags=expected_labels,
                error=type(exc).__name__,
            )
    finally:
        _delete_all(client)
    return outcome


def _delete_all(client: _Client) -> None:
    """Deletes every Contract the evaluation user owns, best effort. A retried upload can leave
    a stored Contract behind, and the user belongs to the harness, so nothing else is lost."""
    try:
        for c in client.get("/contracts").json():
            client.delete(f"/contracts/{c['id']}")
    except Exception:
        log.exception("could not delete the sample Contracts")


def _score_contract(
    outcome: ContractOutcome,
    sample: SampleContract,
    uploaded: dict,
    client: _Client,
    judge: Judge,
    sleep,
) -> None:
    contract_id = uploaded["id"]
    stored = [
        ClauseOut(**c)
        for c in client.get(f"/contracts/{contract_id}").json()["clauses"]
    ]
    brief = uploaded["brief"]
    numbers = {c.number for c in stored}
    flags = brief["flagged_clauses"]
    outcome.found_flags = [
        FoundFlag(
            clause=f["clause_reference"]["number"],
            provisions=[_provision_key(c["act"], c["number"]) for c in f["citations"]],
        )
        for f in flags
    ]
    outcome.expected_found, outcome.found_correct = _flag_scores(
        sample.expected_flags, outcome.found_flags
    )
    # Every Clause number the brief gives, and the text quoted for each flag.
    cited_numbers = [t["clause"] for t in brief["key_terms"]] + [
        n for p in brief["obligations"] for o in p["obligations"] for n in o["clauses"]
    ]
    refs = [ClauseReference(**f["clause_reference"]) for f in flags]
    outcome.clause_references_checked = len(cited_numbers) + len(refs)
    outcome.unverified_clause_references = len(
        [n for n in cited_numbers if n not in numbers]
    ) + len(unverified_clause_references(refs, stored))
    for case in sample.followups:
        outcome.followups.append(
            _evaluate_followup(case, sample, contract_id, stored, client, judge, sleep)
        )


def _evaluate_followup(
    case: FollowUp,
    sample: SampleContract,
    contract_id: str,
    stored: list[ClauseOut],
    client: _Client,
    judge: Judge,
    sleep,
) -> FollowUpOutcome:
    try:
        response = _ask(client, contract_id, case.query, sleep)
        return FollowUpOutcome(
            kind=case.kind,
            query=case.query,
            accurate=_followup_accurate(case, response, judge, sample.id),
            response_type=response.response_type,
            trust_label=response.trust_label,
            answer_language=response.answer_language,
            clause_references=len(response.clause_references),
            unverified_clause_references=len(
                unverified_clause_references(response.clause_references, stored)
            ),
        )
    except Exception as exc:
        log.exception("follow-up %s/%s failed", sample.id, case.kind)
        return FollowUpOutcome(
            kind=case.kind, query=case.query, error=type(exc).__name__
        )


def run_contract_evaluation(
    samples: list[SampleContract], *, client: _Client, judge: Judge, sleep=None
) -> ContractEvaluation:
    """Uploads each sample Contract, scores its brief, asks its follow-ups and deletes it.
    `client` is signed in as a user whose Contracts the harness owns, against a database it may
    write to. A Contract or follow-up that fails after retries is reported and left out of the
    scores."""
    return ContractEvaluation(
        contracts=[_evaluate_contract(s, client, judge, sleep) for s in samples]
    )


# --- report ---------------------------------------------------------------------------------


def _cell(f: FollowUpOutcome) -> str:
    if f.error:
        return f"error ({f.error})"
    refs = f"{f.clause_references} Clause ref" + (
        "" if f.clause_references == 1 else "s"
    )
    return f"{'correct' if f.accurate else 'wrong'} ({f.response_type}, {f.trust_label}, {refs})"


def render_contracts_report(result: ContractEvaluation) -> str:
    """The Contract evaluation as a Markdown section: totals, then each Contract's expected
    against found flags, Hallucinated clause references and follow-up results."""
    out = [
        SECTION_TITLE,
        "",
        "| Metric | Result |",
        "|---|---|",
        f"| Flag recall | {_pct(result.flag_recall)} |",
        f"| Flag precision | {_pct(result.flag_precision)} |",
        f"| Hallucinated clause references (expected 0) | {result.hallucinated_clause_references} of {result.clause_references_checked} checked |",
        f"| Follow-up accuracy | {_pct(result.followup_accuracy)} |",
    ]
    for kind, acc in result.followup_accuracy_by_kind.items():
        out.append(f"| Follow-up accuracy: {kind} | {_pct(acc)} |")
    out.append("")
    for c in result.contracts:
        out += [f"### {c.id}: {c.title}", ""]
        if c.error:
            out += [f"Not scored: the Contract could not be uploaded ({c.error}).", ""]
            continue
        found = [f"{f.clause}: " + ", ".join(f.provisions) for f in c.found_flags]
        out += [
            f"- Expected flags: {'; '.join(c.expected_flags) or 'none'}",
            f"- Found flags: {'; '.join(found) or 'none'}",
            f"- Expected flags found: {c.expected_found} of {len(c.expected_flags)}; found flags that were expected: {c.found_correct} of {len(found)}",
            f"- Hallucinated clause references: {c.unverified_clause_references + sum(f.unverified_clause_references for f in c.followups if f.error is None)}",
            "",
            "| Follow-up | Query | Result |",
            "|---|---|---|",
        ]
        for f in c.followups:
            out.append(f"| {f.kind} | {f.query} | {_cell(f)} |")
        out.append("")
    errored = [f for c in result.contracts for f in c.followups if f.error]
    if errored:
        out += [
            f"{len(errored)} follow-ups failed after retries and are excluded from the metrics.",
            "",
        ]
    out.append(SECTION_END)
    return "\n".join(out) + "\n"


def write_report(path: Path, section: str) -> None:
    """Puts the Contract evaluation section into the report, replacing an earlier one and leaving
    the rest (the `/ask` evaluation) as it is. Creates the file when there is none."""
    existing = path.read_text() if path.exists() else ""
    start = existing.find(SECTION_TITLE)
    if start != -1:
        end = existing.find(SECTION_END, start)
        existing = existing[:start] + (
            existing[end + len(SECTION_END) :].lstrip("\n") if end != -1 else ""
        )
    path.write_text(existing.rstrip("\n") + "\n\n" + section if existing else section)


def keep_contract_section(path: Path, new_report: str) -> str:
    """`new_report` (a fresh `/ask` report) with the Contract evaluation section already in the
    file at `path` carried over, so re-running `/ask` does not erase it."""
    if not path.exists():
        return new_report
    old = path.read_text()
    start = old.find(SECTION_TITLE)
    if start == -1:
        return new_report
    end = old.find(SECTION_END, start)
    if end == -1:
        return new_report
    return new_report.rstrip("\n") + "\n\n" + old[start : end + len(SECTION_END)] + "\n"
