import { describe, expect, it } from "vitest";
import { needsSignIn } from "./protected-routes";

describe("needsSignIn", () => {
  it.each(["/ask", "/ask/", "/contracts", "/contracts/42", "/contracts/42/anything"])(
    "protects %s",
    (path) => expect(needsSignIn(path)).toBe(true),
  );

  it.each(["/", "/law", "/law/Indian%20Penal%20Code", "/law/Constitution%20of%20India/21", "/asking", "/contractsx", "/sign-in"])(
    "leaves %s public",
    (path) => expect(needsSignIn(path)).toBe(false),
  );
});
