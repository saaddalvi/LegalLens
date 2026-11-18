import Link from "next/link";
import type { ActSummary } from "@/lib/ask-types";
import { CORPUS_ACTS, REPLACED_BY, lawHref } from "@/lib/corpus";

// Every Act in the Corpus with how many Provisions it has.
export default function ActsView({ acts }: { acts: ActSummary[] }) {
  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="condensed text-3xl">Browse the law</h1>
        <p className="max-w-[68ch] text-muted">
          Read the Acts LegalLens answers from. A repealed Act&apos;s Provisions point to the
          law that replaced them.
        </p>
      </header>
      <ul>
        {acts.map(({ act, provisions }) => {
          const now = REPLACED_BY[act as (typeof CORPUS_ACTS)[number]];
          return (
            <li key={act} className="border-b border-rule">
              <Link
                href={lawHref(act)}
                className="flex items-baseline justify-between gap-4 py-2.5 hover:bg-ledger"
              >
                <span className={now ? "line-through decoration-redtape decoration-2" : ""}>{act}</span>
                <span className="shrink-0 text-sm text-muted">
                  {now && <>now {now}, </>}
                  {provisions} Provisions
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
