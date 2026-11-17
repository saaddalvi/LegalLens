import "@testing-library/jest-dom/vitest";

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
