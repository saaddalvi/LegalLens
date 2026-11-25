import { describe, expect, it } from "vitest";
import { provisionText } from "./provision-text";

describe("provisionText", () => {
  it("joins lines that only ran out on the printed page", () => {
    expect(provisionText("Every agreement by which any one is restrained from\nexercising a lawful profession is void.")).toBe(
      "Every agreement by which any one is restrained from exercising a lawful profession is void.",
    );
  });

  it("keeps the breaks before sub-sections and their clauses", () => {
    const text =
      "(1) The security deposit shall\nbe such as may be agreed, which shall ––\n(a) not exceed two months rent;\nand\n(b) not exceed six months rent.\n(2) The deposit shall be refunded.";
    expect(provisionText(text)).toBe(
      "(1) The security deposit shall be such as may be agreed, which shall ––\n(a) not exceed two months rent; and\n(b) not exceed six months rent.\n(2) The deposit shall be refunded.",
    );
  });

  it("keeps Explanations, Illustrations and provisos apart", () => {
    const text = "the penalty stipulated for.\nExplanation.—Interest may be a penalty:\nProvided that it is not.\nIllustrations\n(a)A contracts with B.";
    expect(provisionText(text)).toBe(text);
  });

  it("keeps list items that lead on with a comma or an 'or'", () => {
    const text = "who—\n(a) is a citizen of India,\n(b) is over thirty-five, or\n(c) is qualified.";
    expect(provisionText(text)).toBe(text);
  });

  it("does not break where a number is only referred to", () => {
    expect(provisionText("as provided in sub-section\n(1) of section 5, clauses (d), (f),\n(g) and (h) apply.")).toBe(
      "as provided in sub-section (1) of section 5, clauses (d), (f), (g) and (h) apply.",
    );
  });

  it("rejoins a word hyphenated at the end of a line", () => {
    expect(provisionText("under sub-\nsection (4)")).toBe("under sub-section (4)");
  });
});
