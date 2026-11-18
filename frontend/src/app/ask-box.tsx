"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { askHref } from "@/lib/corpus";

// Shared with the asking screen, so both ask boxes look and read the same.
export const FIELD_CLASS =
  "w-full resize-y rounded-t border-0 border-b-2 border-ink bg-ledger px-3 py-2.5 font-serif text-lg leading-relaxed text-ink placeholder:text-muted focus-visible:outline-offset-0";
export const BUTTON_CLASS =
  "rounded bg-ink px-6 py-2.5 text-base font-semibold text-ink-contrast disabled:opacity-50";

export default function AskBox() {
  const router = useRouter();
  const [query, setQuery] = useState("");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    router.push(askHref(q));
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-3">
      <label htmlFor="landing-query" className="font-medium">
        Ask a question about Indian law
      </label>
      <textarea
        id="landing-query"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        rows={3}
        placeholder="In English or Hindi"
        className={FIELD_CLASS}
      />
      <button type="submit" className={`${BUTTON_CLASS} self-start`}>
        Ask
      </button>
    </form>
  );
}
