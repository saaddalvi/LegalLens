"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export default function AskBox() {
  const router = useRouter();
  const [query, setQuery] = useState("");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    router.push(`/ask?${new URLSearchParams({ q })}`);
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
        className="w-full rounded border border-border bg-surface p-2 text-base text-ink"
      />
      <button
        type="submit"
        className="rounded bg-primary px-4 py-3 font-medium text-primary-contrast sm:self-start"
      >
        Ask
      </button>
    </form>
  );
}
