import Link from "next/link";
import { Fragment } from "react";
import type { Provision } from "@/lib/ask-types";
import { lawHref } from "@/lib/corpus";
import { parseRefs } from "@/lib/refs";

export const STATUS_TEXT: Record<Provision["status"], string> = {
  in_force: "in force",
  repealed: "repealed",
  model: "model Act, not in force by itself",
};

// "Bharatiya Nyaya Sanhita 103 and Bharatiya Nyaya Sanhita 104", each one a link to
// that Provision. A value that is not a reference is shown as it is.
export function RefLinks({ value }: { value: string }) {
  const refs = parseRefs(value);
  if (refs.length === 0) return value;
  return refs.map((r, i) => (
    <Fragment key={`${r.act}-${r.number}`}>
      {i > 0 && " and "}
      <Link href={lawHref(r.act, r.number)} className="underline underline-offset-4">
        {r.act} {r.number}
      </Link>
    </Fragment>
  ));
}

// The warnings a Provision carries wherever it is shown: a repealed one points to
// the law that replaced it, and a model Act's is not law in force by itself.
export function ProvisionNotes({ provision }: { provision: Pick<Provision, "status" | "superseded_by"> }) {
  return (
    <>
      {provision.status === "repealed" && (
        <p role="note" className="text-redtape">
          This Provision has been repealed
          {provision.superseded_by ? (
            <>
              . The current law is <RefLinks value={provision.superseded_by} />.
            </>
          ) : (
            "."
          )}
        </p>
      )}
      {provision.status === "model" && (
        <p role="note" className="border-l-4 border-warn-border bg-warn-bg px-3 py-2 text-warn">
          This is a model Act, a template that States may adopt. It is not law in force by
          itself. Your State&apos;s own law may differ, so check it.
        </p>
      )}
    </>
  );
}

// Says which older Provision an in-force one replaced.
export function ReplacesNote({ supersedes }: { supersedes: string }) {
  return (
    <p className="text-muted">
      Replaces <RefLinks value={supersedes} />.
    </p>
  );
}
