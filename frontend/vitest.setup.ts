import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// Components render outside a ClerkProvider in tests; by default the visitor is signed out.
// Tests that care about sign-in mock "@clerk/nextjs" themselves.
vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ isLoaded: true, isSignedIn: false, getToken: async () => null }),
  SignInButton: ({ children }: { children: React.ReactNode }) => children,
  UserButton: () => null,
  ClerkProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// jsdom has no matchMedia. Component tests run with reduced motion, so answers
// appear at once; tests of the reveal animation override this.
window.matchMedia = ((query: string) => ({
  matches: query.includes("prefers-reduced-motion"),
  media: query,
  onchange: null,
  addEventListener: () => {},
  removeEventListener: () => {},
  addListener: () => {},
  removeListener: () => {},
  dispatchEvent: () => false,
})) as typeof window.matchMedia;
