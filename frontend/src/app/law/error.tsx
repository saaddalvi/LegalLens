"use client";

import { BUTTON_CLASS } from "../ask-box";

// Shown when the law cannot be read, for example while the backend is waking up.
export default function LawError({ retry }: { error: unknown; retry: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-start gap-3 border-l-2 border-redtape pl-4">
      <p className="text-redtape">
        We could not load this page. The LegalLens service may be waking up, so please try again in
        a moment.
      </p>
      <button type="button" onClick={() => retry()} className={BUTTON_CLASS}>
        Try again
      </button>
    </div>
  );
}
