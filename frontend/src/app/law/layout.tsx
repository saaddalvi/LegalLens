import type { Metadata } from "next";
import Link from "next/link";
import AccountNav from "../account-nav";
import ThemeToggle from "../theme-toggle";
import { DISCLAIMER } from "@/lib/answer-text";

export const metadata: Metadata = {
  title: "Browse the law | LegalLens",
  description: "Read the Acts and Provisions LegalLens answers from, in full.",
};

// The frame for every page under /law. It reads no params, so it is part of the static shell.
export default function LawLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-4 pb-16 sm:px-8">
      <header className="border-b border-rule pt-5 pb-4">
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-3">
          <p className="condensed text-2xl">
            <Link href="/">LegalLens</Link>
          </p>
          <div className="flex items-center gap-5">
            <nav aria-label="Main" className="flex gap-5 whitespace-nowrap text-sm">
              <Link href="/ask" className="inline-flex min-h-11 items-center underline underline-offset-4">
                Ask a question
              </Link>
              <Link href="/law" className="underline underline-offset-4">
                Browse the law
              </Link>
            </nav>
            <AccountNav />
            <ThemeToggle />
          </div>
        </div>
      </header>
      {children}
      <footer className="border-t border-rule pt-6">
        <p role="note" className="max-w-[68ch] text-sm text-muted">
          {DISCLAIMER}
        </p>
      </footer>
    </main>
  );
}
