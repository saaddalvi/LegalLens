import { BUTTON_CLASS } from "./ask-box";

// The way back after following a link down the page, held at the foot of the screen. Put it
// just after the heading that was jumped to, so it is also the next stop for the Tab key. A
// part of the page that holds it keeps clear of it.
export default function ReturnBar({
  label,
  onBack,
  onStay,
  className = "",
}: {
  // What the reader goes back to: "Back to {label}".
  label: string;
  onBack: () => void;
  onStay: () => void;
  className?: string;
}) {
  return (
    <div data-return-bar className={`fixed inset-x-0 bottom-0 z-10 border-t-2 border-ink bg-paper px-4 pb-[env(safe-area-inset-bottom)] sm:px-8 ${className}`}>
      <div className="mx-auto flex max-w-[44rem] items-center justify-between gap-3 py-2">
        <button type="button" onClick={onBack} className={`${BUTTON_CLASS} min-h-11 min-w-0`}>
          Back to {label}
        </button>
        <button
          type="button"
          aria-label="Stay here"
          title="Stay here"
          onClick={onStay}
          className="inline-flex size-11 shrink-0 items-center justify-center rounded border border-rule hover:border-ink"
        >
          <svg aria-hidden="true" viewBox="0 0 16 16" className="size-[18px]" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M3.5 3.5l9 9M12.5 3.5l-9 9" strokeLinecap="round" />
          </svg>
        </button>
      </div>
    </div>
  );
}
