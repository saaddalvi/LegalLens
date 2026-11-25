// For tests: the part of Next's router that a Contract's page relies on. As in Next, writing
// to the browser's history, or going back through it, changes what usePathname returns.
import { useSyncExternalStore } from "react";

const listeners = new Set<() => void>();
const changed = () => listeners.forEach((l) => l());

for (const method of ["pushState", "replaceState"] as const) {
  const write = window.history[method].bind(window.history);
  window.history[method] = (...args: Parameters<History["pushState"]>) => {
    write(...args);
    changed();
  };
}
window.addEventListener("popstate", changed);

export function usePathname() {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => void listeners.delete(listener);
    },
    () => window.location.pathname,
  );
}

// Opens a page, as typing its address would.
export function visit(path: string) {
  window.history.replaceState(null, "", path);
}
