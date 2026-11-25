import { describe, expect, it } from "vitest";
import { splitMentions } from "./mentions";

const cited = [
  { act: "Constitution of India", number: "22" },
  { act: "Bharatiya Nagarik Suraksha Sanhita", number: "47" },
];

const mentioned = (text: string) =>
  splitMentions(text, cited).filter((s) => "act" in s).map((s) => s.text);

describe("splitMentions", () => {
  it("matches 'Act, Section N' as the model writes it", () => {
    const text =
      "(Constitution of India, Section 22; Bharatiya Nagarik Suraksha Sanhita, Section 47)";
    expect(mentioned(text)).toEqual([
      "Constitution of India, Section 22",
      "Bharatiya Nagarik Suraksha Sanhita, Section 47",
    ]);
  });

  it("still matches the other forms", () => {
    expect(mentioned("BNSS section 47 and Article 22")).toEqual(["BNSS section 47", "Article 22"]);
  });

  it("does not match a bare comma before a number", () => {
    expect(mentioned("Under the BNSS, 47 people")).toEqual([]);
  });
});
