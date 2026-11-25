import { describe, expect, it } from "vitest";
import { DISCLAIMER, answerAsText } from "./answer-text";
import type { AskResponse, Citation } from "./ask-types";

const citation: Citation = {
  act: "Constitution of India",
  chapter: "Part III",
  number: "14",
  status: "in_force",
  text: "The State shall not deny to any person equality before the law.",
  superseded_by: null,
  supersedes: null,
};

const answer: AskResponse = {
  response_type: "answer",
  refusal_reason: null,
  suggested_reformulation: null,
  answer: "Equality before the law is guaranteed.",
  answer_language: "en",
  trust_label: "corpus",
  citations: [citation],
  fallback_sources: [],
};

describe("answerAsText", () => {
  it("lists the Trust label, the answer, its Citations and the disclaimer", () => {
    expect(answerAsText(answer)).toBe(
      `From statute text\n\nEquality before the law is guaranteed.\n\nCitations:\n- Constitution of India, 14\n\n${DISCLAIMER}`,
    );
  });

  it("flags a repealed Provision with what replaced it", () => {
    const text = answerAsText({
      ...answer,
      citations: [
        {
          ...citation,
          act: "Indian Penal Code",
          number: "302",
          status: "repealed",
          superseded_by: "Bharatiya Nyaya Sanhita 103; Bharatiya Nyaya Sanhita 104",
        },
      ],
    });
    expect(text).toContain(
      "- Indian Penal Code, 302 (repealed; now Bharatiya Nyaya Sanhita 103 and Bharatiya Nyaya Sanhita 104)",
    );
  });

  it("flags a repealed Provision with nothing to replace it", () => {
    const text = answerAsText({ ...answer, citations: [{ ...citation, status: "repealed" }] });
    expect(text).toContain("- Constitution of India, 14 (repealed)");
  });

  it("flags a model Act Provision as not law in force by itself", () => {
    const text = answerAsText({
      ...answer,
      citations: [{ ...citation, act: "Model Tenancy Act", number: "11", status: "model" }],
    });
    expect(text).toContain("- Model Tenancy Act, 11 (model Act, not in force by itself)");
  });

  it("lists web sources with their addresses", () => {
    const text = answerAsText({
      ...answer,
      trust_label: "corpus_and_fallback",
      fallback_sources: [{ title: "RTI fees", url: "https://rti.gov.in/fees", snippet: "..." }],
    });
    expect(text).toContain("Web sources:\n- RTI fees (https://rti.gov.in/fees)");
  });

  it("leaves out sections that are empty", () => {
    const text = answerAsText({ ...answer, citations: [] });
    expect(text).toBe(`From statute text\n\nEquality before the law is guaranteed.\n\n${DISCLAIMER}`);
  });
});
