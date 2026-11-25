import Link from "next/link";
import AccountNav from "./account-nav";
import ThemeToggle from "./theme-toggle";

export const LINKS = [
  { section: "ask", href: "/ask", label: "Ask a question" },
  { section: "contracts", href: "/contracts", label: "Your Contracts" },
  { section: "law", href: "/law", label: "Browse the law" },
] as const;

export type Section = (typeof LINKS)[number]["section"];

// The header of every screen after the landing page. On phones the links take a row of
// their own under the wordmark. `omit` leaves out a section a page should not offer.
// `compact` is for a page that fills the window: a single shallow row, which on phones leaves
// the links to the page's own menu.
export default function SiteHeader({
  current,
  omit,
  compact = false,
}: {
  current: Section;
  omit?: Section;
  compact?: boolean;
}) {
  return (
    <header className={`border-b border-rule ${compact ? "shrink-0 px-4 py-1" : "pt-5 pb-2 sm:pb-4"}`}>
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1">
        <p className="condensed mr-auto text-2xl">
          <Link href="/" className="inline-flex min-h-11 items-center">
            LegalLens
          </Link>
        </p>
        <nav
          aria-label="Main"
          className={`order-last w-full flex-wrap gap-x-2.5 text-sm min-[22.5rem]:gap-x-5 sm:order-none sm:flex sm:w-auto ${compact ? "hidden" : "flex"}`}
        >
          {LINKS.filter((l) => l.section !== omit).map((l) => (
            <Link
              key={l.section}
              href={l.href}
              aria-current={l.section === current ? "true" : undefined}
              className="inline-flex min-h-11 items-center whitespace-nowrap underline decoration-rule underline-offset-4 hover:decoration-ink aria-[current]:font-semibold aria-[current]:decoration-ink aria-[current]:decoration-2"
            >
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-4">
          <AccountNav />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
