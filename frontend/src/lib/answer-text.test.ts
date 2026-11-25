import { describe, expect, it } from "vitest";
import { CHECK_YOUR_COPY, DISCLAIMER, answerAsText } from "./answer-text";
import type { AskResponse, Citation } from "./ask-types";
import { TRUST_EXPLANATION } from "./trust-labels";

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

const context = { query: "What is Article 14?", origin: "https://legallens.test" };
const asText = (result: Parameters<typeof answerAsText>[0]) => answerAsText(result, context);

describe("answerAsText", () => {
  it("gives the question, Trust label, answer, each Citation in full and the disclaimer", () => {
    expect(asText(answer)).toBe(
      [
        "Question: What is Article 14?",
        "From statute text",
        "Equality before the law is guaranteed.",
        "Citations:\n- Constitution of India, Article 14\n" +
          "  The State shall not deny to any person equality before the law.\n" +
          "  https://legallens.test/law/Constitution%20of%20India/14",
        DISCLAIMER,
      ].join("\n\n"),
    );
  });

  it("quotes the Contract's Clauses, with the reminder to check them", () => {
    const text = asText({
      ...answer,
      trust_label: "contract",
      citations: [],
      clause_references: [
        { number: "0", text: "RENT AGREEMENT" },
        { number: "7.2", text: "7.2 Notice\nNotice is two months." },
      ],
    });
    expect(text).toContain(
      `From your Contract:\n${CHECK_YOUR_COPY}\n- Recitals and parties\n  RENT AGREEMENT\n` +
        "- Clause 7.2\n  7.2 Notice\n  Notice is two months.",
    );
  });

  it("explains a Trust label that needs it, as the screen does", () => {
    const text = asText({ ...answer, trust_label: "fallback" });
    expect(text).toContain(`From web sources (less reliable)\n${TRUST_EXPLANATION.fallback}`);
  });

  it("flags a repealed Provision with what replaced it", () => {
    const text = asText({
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
      "- Indian Penal Code, Section 302 (repealed; now Bharatiya Nyaya Sanhita, Section 103 and Bharatiya Nyaya Sanhita, Section 104)",
    );
  });

  it("flags a repealed Provision with nothing to replace it", () => {
    const text = asText({ ...answer, citations: [{ ...citation, status: "repealed" }] });
    expect(text).toContain("- Constitution of India, Article 14 (repealed)");
  });

  it("flags a model Act Provision as not law in force by itself", () => {
    const text = asText({
      ...answer,
      citations: [{ ...citation, act: "Model Tenancy Act", number: "11", status: "model" }],
    });
    expect(text).toContain("- Model Tenancy Act, Section 11 (model Act, not in force by itself)");
  });

  it("lists web sources with their addresses", () => {
    const text = asText({
      ...answer,
      trust_label: "corpus_and_fallback",
      fallback_sources: [{ title: "RTI fees", url: "https://rti.gov.in/fees", snippet: "..." }],
    });
    expect(text).toContain("Web sources:\n- RTI fees (https://rti.gov.in/fees)");
  });

  it("leaves out sections that are empty", () => {
    const text = asText({ ...answer, citations: [] });
    expect(text).toBe(
      `Question: What is Article 14?\n\nFrom statute text\n\nEquality before the law is guaranteed.\n\n${DISCLAIMER}`,
    );
  });
});
