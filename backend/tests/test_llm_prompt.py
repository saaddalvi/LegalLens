"""What the LLM is shown about each Provision."""

from legallens.llm import _PROMPT, GeminiLLM
from legallens.models import Provision


def provision(status):
    return Provision(
        act="Model Tenancy Act", chapter="Chapter III", number="11", status=status, text="Deposit."
    )


def test_model_act_provision_is_marked_for_the_llm():
    assert GeminiLLM._format([provision("model")]) == "[Act: Model Tenancy Act | Section: 11] (model) Deposit."


def test_in_force_provision_is_left_unmarked():
    assert GeminiLLM._format([provision("in_force")]) == "[Act: Model Tenancy Act | Section: 11] Deposit."


def test_prompt_tells_the_llm_a_model_act_is_a_template_to_check_against_state_law():
    assert '"model"' in _PROMPT and "template" in _PROMPT and "State" in _PROMPT


def test_prompt_tells_the_llm_to_answer_from_web_sources_when_there_are_no_provisions():
    assert "no Provisions" in _PROMPT and "web sources" in _PROMPT


def test_citation_schema_tells_the_llm_to_give_act_name_and_number_separately():
    # Hindi answers once came back with "Consumer Protection Act 35" in the act field,
    # which the Hallucinated-citation check rightly rejected.
    from legallens.llm import ProvisionRef

    fields = ProvisionRef.model_fields
    assert "without the number" in (fields["act"].description or "")
    assert "one" in (fields["number"].description or "")
