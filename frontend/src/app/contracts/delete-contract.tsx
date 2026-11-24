"use client";

import { useAuth } from "@clerk/nextjs";
import { useState } from "react";
import { BUTTON_CLASS } from "../ask-box";
import { API_URL } from "@/lib/api-url";

// Delete with a confirmation step. Deleting removes the Contract, its Clauses and its
// conversation for good, so nothing is sent until the user confirms.
export default function DeleteContract({
  contractId,
  title,
  onDeleted,
}: {
  contractId: string;
  title: string;
  onDeleted: () => void;
}) {
  const { getToken } = useAuth();
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function remove() {
    setBusy(true);
    setError(null);
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/contracts/${encodeURIComponent(contractId)}`, {
        method: "DELETE",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      // 404: already gone, which is what the user wanted.
      if (res.ok || res.status === 404) return onDeleted();
      setError("We could not delete that Contract. Please try again.");
    } catch {
      setError("We could not delete that Contract. Check your connection and try again.");
    }
    setBusy(false);
  }

  if (!confirming)
    return (
      <button
        type="button"
        aria-label={`Delete ${title}`}
        onClick={() => setConfirming(true)}
        className="self-start text-sm text-muted underline underline-offset-4"
      >
        Delete
      </button>
    );
  return (
    <div className="flex flex-col items-start gap-2">
      <p className="text-sm">Delete this Contract? Its Clauses and conversation are deleted too. This cannot be undone.</p>
      <div className="flex gap-3">
        <button type="button" disabled={busy} onClick={() => void remove()} className={BUTTON_CLASS}>
          Yes, delete
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            setConfirming(false);
            setError(null);
          }}
          className="underline underline-offset-4"
        >
          Cancel
        </button>
      </div>
      {error && (
        <p role="alert" className="text-redtape">
          {error}
        </p>
      )}
    </div>
  );
}
