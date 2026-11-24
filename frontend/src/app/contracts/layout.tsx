import type { Metadata } from "next";
import Link from "next/link";
import AccountNav from "../account-nav";
import ThemeToggle from "../theme-toggle";
import { DISCLAIMER } from "@/lib/answer-text";

export const metadata: Metadata = {
  title: "Your Contracts | LegalLens",
  description: "Upload a Contract and see its Clauses.",
};

// The frame for every page under /contracts.
export default function ContractsLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-4 pb-16 sm:px-8">
      <header className="flex flex-col gap-3 border-b border-rule pt-5 pb-4">
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-3">
          <p className="condensed text-2xl">
            <Link href="/">LegalLens</Link>
          </p>
          <div className="flex items-center gap-5">
            <nav aria-label="Main" className="flex gap-5 whitespace-nowrap text-sm">
              <Link href="/ask" className="underline underline-offset-4">
                Ask a question
              </Link>
              <Link href="/contracts" className="underline underline-offset-4">
                Your Contracts
              </Link>
              <Link href="/law" className="underline underline-offset-4">
                Browse the law
              </Link>
            </nav>
            <AccountNav />
            <ThemeToggle />
          </div>
        </div>
        <p role="note" className="text-sm text-muted">
          {DISCLAIMER}
        </p>
      </header>
      {children}
    </main>
  );
}
