import type { Metadata } from "next";
import SiteHeader from "../site-header";
import { DISCLAIMER } from "@/lib/answer-text";

export const metadata: Metadata = {
  title: "Your Contracts | LegalLens",
  description: "Upload a Contract and see its Clauses.",
};

// The frame for every page under /contracts.
export default function ContractsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-4 pb-16 sm:px-8">
      <SiteHeader current="contracts" />
      <main className="flex flex-col gap-8">{children}</main>
      <footer className="border-t border-rule pt-6">
        <p role="note" className="measure text-sm text-muted">
          {DISCLAIMER}
        </p>
      </footer>
    </div>
  );
}
