"use client";

import { useRouter } from "next/navigation";
import { useId, useState } from "react";
import { askHref } from "@/lib/corpus";

// Shared with the asking screen, so both ask boxes look and read the same.
export const FIELD_CLASS =
  "w-full resize-y rounded-t border-0 border-b-2 border-ink bg-ledger px-3 py-2.5 font-serif text-lg leading-relaxed text-ink placeholder:text-muted focus-visible:outline-offset-0";
export const BUTTON_CLASS =
  "rounded bg-ink px-6 py-2.5 text-base font-semibold text-ink-contrast hover:bg-ink/85 disabled:opacity-50 disabled:hover:bg-ink";

// A button that cannot act yet stays focusable (aria-disabled, not disabled), and looks it.
export const DIMMED_BUTTON_CLASS =
  "aria-disabled:bg-ledger aria-disabled:text-muted aria-disabled:hover:bg-ledger";
export const BUSY_BUTTON_CLASS = `aria-disabled:cursor-progress ${DIMMED_BUTTON_CLASS}`;

export default function AskBox() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [missing, setMissing] = useState(false);
  const hintId = useId();

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q) {
      setMissing(true);
      return;
    }
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
        onChange={(e) => {
          setQuery(e.target.value);
          setMissing(false);
        }}
        rows={3}
        aria-required="true"
        aria-invalid={missing || undefined}
        aria-describedby={hintId}
        placeholder="In English or Hindi"
        className={FIELD_CLASS}
      />
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <button type="submit" className={BUTTON_CLASS}>
          Ask
        </button>
        {/* Always in the page so a screen reader announces the text when it appears. */}
        <p id={hintId} role="status" aria-live="polite" className="font-medium">
          {missing ? "Type your question first, in English or Hindi." : ""}
        </p>
      </div>
    </form>
  );
}
