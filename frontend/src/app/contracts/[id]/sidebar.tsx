import { useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import Link from "next/link";
import { LINKS } from "../../site-header";

// From this width the sidebar is always beside the page (Tailwind's lg).
const WIDE = "(min-width: 64rem)";
const ID = "contract-sidebar";

// Below that width the sidebar is a drawer over the page, opened by a button.
export function useSidebar() {
  const [open, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null);
  const drawer = useRef<HTMLElement>(null);

  function show() {
    flushSync(() => setOpen(true));
    drawer.current?.querySelector<HTMLElement>("nav a")?.focus();
  }
  // Closed by the reader, who goes back to the button that opened it.
  function close() {
    flushSync(() => setOpen(false));
    button.current?.focus();
  }

  // A window widened past the drawer's width has no drawer left to close.
  useEffect(() => {
    if (!open || typeof window.matchMedia !== "function") return;
    const wide = window.matchMedia(WIDE);
    const apply = () => {
      if (wide.matches) setOpen(false);
    };
    wide.addEventListener?.("change", apply);
    return () => wide.removeEventListener?.("change", apply);
  }, [open]);

  return { open, buttonRef: button, drawerRef: drawer, show, close, dismiss: () => setOpen(false) };
}

type Menu = ReturnType<typeof useSidebar>;

export function MenuButton({ menu, count }: { menu: Menu; count: number }) {
  const { open, buttonRef, show } = menu;
  const label = count > 0 ? `Show conversations (${count})` : "Show conversations";
  return (
    <button
      ref={buttonRef}
      type="button"
      aria-label={label}
      title={label}
      aria-expanded={open}
      aria-controls={ID}
      onClick={show}
      className="-ml-2 inline-flex size-11 shrink-0 items-center justify-center rounded hover:bg-ledger lg:hidden"
    >
      <svg aria-hidden="true" viewBox="0 0 16 16" className="size-5" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M2 4h12M2 8h12M2 12h8" strokeLinecap="round" />
      </svg>
    </button>
  );
}

// The way back to the list of Contracts, then whatever the page puts here. As a drawer it also
// carries the site's links, which the header has no room for on a phone.
export default function Sidebar({ menu, children }: { menu: Menu; children: React.ReactNode }) {
  const { open, drawerRef, close } = menu;
  return (
    <>
      {open && (
        // A pointer's way out. The keyboard has the button inside, and Escape.
        <div aria-hidden="true" onClick={close} className="fixed inset-0 z-20 bg-ink/40 lg:hidden dark:bg-paper/70" />
      )}
      <aside
        id={ID}
        ref={drawerRef}
        aria-label="This Contract's conversations"
        onKeyDown={(e) => {
          // Escape inside a delete confirmation dismisses that, and is not for the drawer.
          if (e.key === "Escape" && open && !e.defaultPrevented) close();
        }}
        className={`${open ? "fixed inset-y-0 left-0 z-30 flex w-[min(20rem,85vw)]" : "hidden"} flex-col gap-3 border-r border-rule bg-ledger py-3 lg:static lg:z-auto lg:flex lg:w-72`}
      >
        <div className="flex shrink-0 items-center justify-between gap-2 px-6">
          <Link href="/contracts" className="inline-flex min-h-11 items-center text-sm text-muted underline underline-offset-4 hover:text-ink">
            Your Contracts
          </Link>
          {open && (
            <button
              type="button"
              aria-label="Hide conversations"
              title="Hide conversations"
              onClick={close}
              className="-mr-3 inline-flex size-11 items-center justify-center rounded hover:bg-paper lg:hidden"
            >
              <svg aria-hidden="true" viewBox="0 0 16 16" className="size-[18px]" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M3.5 3.5l9 9M12.5 3.5l-9 9" strokeLinecap="round" />
              </svg>
            </button>
          )}
        </div>
        {children}
        {open && (
          <nav aria-label="Elsewhere" className="mt-auto flex shrink-0 flex-col border-t border-rule px-6 pt-2 sm:hidden">
            {LINKS.filter((l) => l.section !== "contracts").map((l) => (
              <Link key={l.section} href={l.href} className="inline-flex min-h-11 items-center underline underline-offset-4">
                {l.label}
              </Link>
            ))}
          </nav>
        )}
      </aside>
    </>
  );
}
