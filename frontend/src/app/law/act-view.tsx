import Link from "next/link";
import type { ActIndex, ProvisionSummary } from "@/lib/ask-types";
import { lawHref } from "@/lib/corpus";

// Consecutive Provisions of the same chapter, in the order the Act prints them.
function byChapter(provisions: ProvisionSummary[]) {
  const groups: { chapter: string; provisions: ProvisionSummary[] }[] = [];
  for (const p of provisions) {
    const last = groups[groups.length - 1];
    if (last?.chapter === p.chapter) last.provisions.push(p);
    else groups.push({ chapter: p.chapter, provisions: [p] });
  }
  return groups;
}

// An Act's Provisions, grouped by chapter, each linking to its full text.
export default function ActView({ index }: { index: ActIndex }) {
  return (
    <div className="flex flex-col gap-8">
      <nav aria-label="Breadcrumb" className="text-sm text-muted">
        <Link href="/law" className="underline underline-offset-4">
          All Acts
        </Link>
      </nav>
      <header className="flex flex-col gap-1">
        <h1 className="condensed text-3xl">{index.act}</h1>
        <p className="text-muted">{index.provisions.length} Provisions</p>
      </header>
      {byChapter(index.provisions).map((group, i) => (
        <section key={`${i}-${group.chapter}`} aria-label={group.chapter} className="flex flex-col gap-2">
          <h2 className="condensed text-xl">{group.chapter}</h2>
          <ul>
            {group.provisions.map((p) => (
              <li key={p.number} className="border-b border-rule">
                <Link
                  href={lawHref(index.act, p.number)}
                  className="flex items-baseline gap-4 py-2 hover:bg-ledger"
                >
                  <span
                    className={`w-14 shrink-0 font-semibold ${
                      p.status === "repealed" ? "line-through decoration-redtape decoration-2" : ""
                    }`}
                  >
                    {p.number}
                  </span>
                  <span className="min-w-0 break-words text-muted">{p.snippet}</span>
                  {p.status !== "in_force" && (
                    <span className="shrink-0 text-sm text-muted">
                      {p.status === "repealed" ? "repealed" : "model Act"}
                    </span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
