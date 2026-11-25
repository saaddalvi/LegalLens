import SiteHeader from "../site-header";
import { DISCLAIMER } from "@/lib/answer-text";

// The frame of the list of Contracts. A Contract's own page fills the window instead.
export default function ContractsFrame({ children }: { children: React.ReactNode }) {
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
