import { beforeEach, describe, expect, it, vi } from "vitest";

const protect = vi.fn();
type Handler = (auth: { protect: () => Promise<void> }, req: { nextUrl: { pathname: string } }) => Promise<void>;
let handler: Handler;
vi.mock("@clerk/nextjs/server", () => ({
  clerkMiddleware: (h: Handler) => {
    handler = h;
    return h;
  },
}));

beforeEach(async () => {
  protect.mockReset();
  await import("./proxy");
});

const visit = (pathname: string) => handler({ protect }, { nextUrl: { pathname } });

describe("proxy", () => {
  it("makes a signed-out visitor to /ask or /contracts sign in", async () => {
    await visit("/ask");
    await visit("/contracts/7");
    expect(protect).toHaveBeenCalledTimes(2);
  });

  it("lets the landing page and /law render signed out", async () => {
    await visit("/");
    await visit("/law/Indian%20Penal%20Code/302");
    expect(protect).not.toHaveBeenCalled();
  });
});
