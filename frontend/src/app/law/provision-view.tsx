import Link from "next/link";
import { ProvisionNotes, ReplacesNote, STATUS_TEXT } from "../provision-notes";
import type { Provision } from "@/lib/ask-types";
import { askAboutProvision, askHref, lawHref, provisionName } from "@/lib/corpus";

// One Provision in full, with the warnings it carries and its place in its Act.
export default function ProvisionView({ provision: p }: { provision: Provision }) {
  const repealed = p.status === "repealed";
  return (
    <article className="flex flex-col gap-6">
      <nav aria-label="Breadcrumb" className="text-sm text-muted">
        <Link href="/law" className="underline underline-offset-4">
          All Acts
        </Link>
        {" / "}
        <Link href={lawHref(p.act)} className="underline underline-offset-4">
          {p.act}
        </Link>
      </nav>

      <header className="flex flex-col gap-1">
        <h1 className="condensed text-3xl">
          <span className={repealed ? "line-through decoration-redtape decoration-2" : ""}>
            {provisionName(p)}
          </span>
        </h1>
        <p className="text-muted">
          {p.chapter}, {STATUS_TEXT[p.status]}
        </p>
      </header>

      <div className="flex flex-col gap-2">
        <ProvisionNotes provision={p} />
        {p.supersedes && <ReplacesNote supersedes={p.supersedes} />}
      </div>

      <blockquote className="break-words bg-ledger px-4 py-3 font-serif text-lg leading-relaxed">
        <p lang="en" className="measure">
          {p.text}
        </p>
      </blockquote>

      <p>
        <Link
          href={askHref(askAboutProvision(p.act, p.number))}
          className="underline underline-offset-4"
        >
          Ask LegalLens about this Provision
        </Link>
      </p>
    </article>
  );
}
