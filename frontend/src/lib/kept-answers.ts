// The answers /ask has shown, kept in the tab's sessionStorage so that returning to a Query, or
// reloading, shows its answer again without asking. They belong to one user at a time: another
// user sees none of them, and the first answer kept for that user replaces them.
import type { AskResponse } from "./ask-types";

// Change the version when AskResponse changes shape.
const KEY = "legallens.ask.answers.v1";
// The oldest goes once there are more than this.
const LIMIT = 20;

type Kept = { user: string; answers: [query: string, answer: AskResponse][] };

// What sessionStorage refused to take (blocked, or full), held for as long as the page lives.
let unsaved: string | null = null;
// The text last read, parsed, so that an unchanged answer is the same object each time.
let last: { raw: string; kept: Kept | null } | null = null;

function parse(raw: string): Kept | null {
  try {
    const kept = JSON.parse(raw) as Kept | null;
    return Array.isArray(kept?.answers) ? kept : null;
  } catch {
    return null;
  }
}

function read(user: string): Kept["answers"] {
  let raw = unsaved;
  try {
    raw ??= window.sessionStorage.getItem(KEY);
  } catch {
    // Storage is blocked.
  }
  if (raw === null) return [];
  if (last?.raw !== raw) last = { raw, kept: parse(raw) };
  return last.kept?.user === user ? last.kept.answers : [];
}

export function keptAnswer(user: string, query: string): AskResponse | null {
  return read(user).find(([q]) => q === query)?.[1] ?? null;
}

export function keepAnswer(user: string, query: string, answer: AskResponse) {
  const others = read(user).filter(([q]) => q !== query);
  const kept: Kept = { user, answers: [...others, [query, answer] as Kept["answers"][number]].slice(-LIMIT) };
  const raw = JSON.stringify(kept);
  try {
    window.sessionStorage.setItem(KEY, raw);
    unsaved = null;
  } catch {
    unsaved = raw;
  }
}
