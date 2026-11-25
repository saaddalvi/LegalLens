import type { Metadata } from "next";
import SiteHeader from "../site-header";
import { DISCLAIMER } from "@/lib/answer-text";

export const metadata: Metadata = {
  title: "Browse the law | LegalLens",
  description: "Read the Acts and Provisions LegalLens answers from, in full.",
};

// The frame for every page under /law. It reads no params, so it is part of the static shell.
export default function LawLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-4 pb-16 sm:px-8">
      <SiteHeader current="law" omit="contracts" />
      {children}
      <footer className="border-t border-rule pt-6">
        <p role="note" className="max-w-[68ch] text-sm text-muted">
          {DISCLAIMER}
        </p>
      </footer>
    </main>
  );
}
