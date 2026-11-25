import Link from "next/link";

export default function LawNotFound() {
  return (
    <div className="flex flex-col items-start gap-3">
      <h1 className="condensed text-3xl">Not in the Corpus</h1>
      <p className="measure text-muted">
        LegalLens has no such Act or Provision. Check the address, or look through the Acts it covers.
      </p>
      <Link href="/law" className="underline underline-offset-4">
        Browse the law
      </Link>
    </div>
  );
}
