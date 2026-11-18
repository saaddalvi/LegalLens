import { describe, expect, it } from "vitest";
import { lawHref } from "./corpus";
import { parseRefs } from "./refs";

describe("parseRefs", () => {
  it("reads one reference", () => {
    expect(parseRefs("Bharatiya Nyaya Sanhita 103")).toEqual([
      { act: "Bharatiya Nyaya Sanhita", number: "103" },
    ]);
  });

  it("reads several, split at the last space of each", () => {
    expect(parseRefs("Bharatiya Nyaya Sanhita 103; Bharatiya Nyaya Sanhita 104A")).toEqual([
      { act: "Bharatiya Nyaya Sanhita", number: "103" },
      { act: "Bharatiya Nyaya Sanhita", number: "104A" },
    ]);
  });

  it("keeps a comma in an Act name", () => {
    expect(parseRefs("Occupational Safety, Health and Working Conditions Code 5")).toEqual([
      { act: "Occupational Safety, Health and Working Conditions Code", number: "5" },
    ]);
  });

  it("reads nothing from nothing, or from something that is not a reference", () => {
    expect(parseRefs(null)).toEqual([]);
    expect(parseRefs("")).toEqual([]);
    expect(parseRefs("nonsense")).toEqual([]);
  });
});

describe("lawHref", () => {
  it("addresses an Act, with its name encoded", () => {
    expect(lawHref("Constitution of India")).toBe("/law/Constitution%20of%20India");
  });

  it("addresses a Provision", () => {
    expect(lawHref("Constitution of India", "21A")).toBe("/law/Constitution%20of%20India/21A");
  });

  it("encodes a comma in an Act name", () => {
    expect(lawHref("Occupational Safety, Health and Working Conditions Code", "1")).toBe(
      "/law/Occupational%20Safety%2C%20Health%20and%20Working%20Conditions%20Code/1",
    );
  });
});

describe("decodeParam", () => {
  it("decodes an encoded Act name and leaves a decoded one alone", async () => {
    const { decodeParam } = await import("./corpus");
    expect(decodeParam("Constitution%20of%20India")).toBe("Constitution of India");
    expect(decodeParam("Constitution of India")).toBe("Constitution of India");
    expect(decodeParam("Occupational%20Safety%2C%20Health")).toBe("Occupational Safety, Health");
  });

  it("returns what it cannot decode", async () => {
    const { decodeParam } = await import("./corpus");
    expect(decodeParam("100%")).toBe("100%");
  });
});

describe("askAboutProvision", () => {
  it("names the Act and the number", async () => {
    const { askAboutProvision } = await import("./corpus");
    expect(askAboutProvision("Bharatiya Nyaya Sanhita", "103")).toBe(
      "What does Bharatiya Nyaya Sanhita 103 say?",
    );
  });

  it("calls a Constitution Provision an Article", async () => {
    const { askAboutProvision } = await import("./corpus");
    expect(askAboutProvision("Constitution of India", "21")).toBe(
      "What does Article 21 of the Constitution of India say?",
    );
  });
});
