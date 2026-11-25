"use client";

import { useAuth } from "@clerk/nextjs";
import { useId, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { BUSY_BUTTON_CLASS, BUTTON_CLASS } from "../ask-box";
import { API_URL } from "@/lib/api-url";
import SignInAgain, { sessionMessage } from "./sign-in-again";

type Failure = "session" | "unavailable" | "unreachable";

// Delete with a confirmation step. Deleting removes the Contract, its Clauses and its
// conversation for good, so nothing is sent until the user confirms. Focus follows the step:
// to Cancel when the question appears, back to Delete when it is dismissed. Where focus goes
// after a delete is the caller's job, in `onDeleted`.
export default function DeleteContract({
  contractId,
  title,
  returnTo,
  onDeleted,
}: {
  contractId: string;
  title: string;
  // Where signing in again comes back to.
  returnTo?: string;
  onDeleted: () => void;
}) {
  const { getToken, isSignedIn } = useAuth();
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<Failure | null>(null);
  const opener = useRef<HTMLButtonElement>(null);
  const cancelButton = useRef<HTMLButtonElement>(null);
  const questionId = useId();

  function ask() {
    flushSync(() => setConfirming(true));
    cancelButton.current?.focus();
  }

  function dismiss() {
    if (busy) return;
    flushSync(() => {
      setConfirming(false);
      setFailure(null);
    });
    opener.current?.focus();
  }

  // The buttons stay focusable while the request is out, so a second press is ignored here.
  async function remove() {
    if (busy) return;
    const refused = failure === "session";
    setBusy(true);
    setFailure(null);
    try {
      // A token the service just refused must not be sent again from the cache.
      const token = await getToken(refused ? { skipCache: true } : undefined);
      const res = await fetch(`${API_URL}/contracts/${encodeURIComponent(contractId)}`, {
        method: "DELETE",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      // 404: already gone, which is what the user wanted.
      if (res.ok || res.status === 404) return onDeleted();
      setFailure(res.status === 401 ? "session" : "unavailable");
    } catch {
      setFailure("unreachable");
    }
    setBusy(false);
  }

  if (!confirming)
    return (
      <button
        ref={opener}
        type="button"
        aria-label={`Delete ${title}`}
        onClick={ask}
        className="self-start text-sm text-muted underline underline-offset-4"
      >
        Delete
      </button>
    );
  return (
    <div
      onKeyDown={(e) => {
        if (e.key === "Escape") dismiss();
      }}
      className="flex flex-col items-start gap-2"
    >
      <p id={questionId} className="text-sm">
        Delete this Contract? Its Clauses and conversation are deleted too. This cannot be undone.
      </p>
      <div className="flex gap-3">
        <button
          type="button"
          aria-disabled={busy || undefined}
          onClick={() => void remove()}
          className={`${BUTTON_CLASS} ${BUSY_BUTTON_CLASS}`}
        >
          {busy ? "Deleting…" : "Yes, delete"}
        </button>
        <button
          ref={cancelButton}
          type="button"
          aria-disabled={busy || undefined}
          aria-describedby={questionId}
          onClick={dismiss}
          className="underline underline-offset-4 aria-disabled:text-muted"
        >
          Cancel
        </button>
      </div>
      {failure && (
        <div role="alert" className="flex flex-col items-start gap-2">
          <p className="text-redtape">
            {failure === "session"
              ? sessionMessage(isSignedIn, "delete this Contract")
              : failure === "unreachable"
                ? "We could not delete that Contract. Check your connection and try again."
                : "We could not delete that Contract. Please try again."}
          </p>
          {failure === "session" && isSignedIn === false && <SignInAgain returnTo={returnTo} />}
        </div>
      )}
    </div>
  );
}
