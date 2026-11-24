"""Reading an uploaded PDF and checking a Contract through Gemini, with a fake chat model."""

import base64

from legallens.llm import ContractCheck, GeminiLLM


class Reply:
    def __init__(self, content):
        self.content = content


class ReadingChat:
    def __init__(self, content="1. Term\nEleven months."):
        self.messages = None
        self._content = content

    def invoke(self, messages):
        self.messages = messages
        return Reply(self._content)

    def with_fallbacks(self, others):
        return self

    def with_structured_output(self, schema):
        self.schema = schema
        return self

    def check(self, prompt):
        self.prompt = prompt


def test_read_document_sends_the_pdf_as_a_file_part_and_returns_the_text():
    chat = ReadingChat()
    llm = GeminiLLM("m", reader_chat_factory=lambda name: chat)
    assert (
        llm.read_document(b"%PDF-1.4 bytes", "application/pdf")
        == "1. Term\nEleven months."
    )
    parts = chat.messages[0].content
    file_part = next(p for p in parts if p["type"] == "file")
    assert file_part["mime_type"] == "application/pdf"
    assert base64.b64decode(file_part["base64"]) == b"%PDF-1.4 bytes"
    assert "Do not summarise" in next(p for p in parts if p["type"] == "text")["text"]


def test_read_document_joins_text_blocks():
    chat = ReadingChat([{"type": "text", "text": "A"}, "B"])
    llm = GeminiLLM("m", reader_chat_factory=lambda name: chat)
    assert llm.read_document(b"x", "application/pdf") == "AB"


class CheckingChat:
    def __init__(self):
        self.prompts = []

    def with_structured_output(self, schema):
        assert schema is ContractCheck
        return self

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return ContractCheck(is_contract=True, is_english=True, title="Rent agreement")


def test_check_contract_fences_the_text_as_untrusted():
    chat = CheckingChat()
    out = GeminiLLM("m", chat_factory=lambda name: chat).check_contract(
        "RENT AGREEMENT ..."
    )
    assert out.title == "Rent agreement"
    assert "<document>\nRENT AGREEMENT ...\n</document>" in chat.prompts[0]
    assert "untrusted" in chat.prompts[0]
