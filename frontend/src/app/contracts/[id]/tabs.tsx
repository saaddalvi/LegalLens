// The parts of a Contract's page, one in front at a time, and the tabs that choose between them.
export type Tab = "chat" | "brief" | "contract";
export type TabEntry = { id: Tab; label: string };

const tabId = (id: Tab) => `tab-${id}`;
const panelId = (id: Tab) => `panel-${id}`;

export default function Tabs({
  tabs,
  current,
  onChoose,
}: {
  tabs: TabEntry[];
  current: Tab;
  onChoose: (tab: Tab) => void;
}) {
  // Arrows, Home and End move along the tabs, as in any set of them.
  function onKeyDown(e: React.KeyboardEvent) {
    const at = tabs.findIndex((t) => t.id === current);
    const to = {
      ArrowLeft: (at - 1 + tabs.length) % tabs.length,
      ArrowRight: (at + 1) % tabs.length,
      Home: 0,
      End: tabs.length - 1,
    }[e.key];
    if (to === undefined) return;
    e.preventDefault();
    onChoose(tabs[to].id);
    document.getElementById(tabId(tabs[to].id))?.focus();
  }
  return (
    <div role="tablist" aria-label="Parts of this Contract" onKeyDown={onKeyDown} className="flex gap-6">
      {tabs.map((t) => (
        <button
          key={t.id}
          id={tabId(t.id)}
          type="button"
          role="tab"
          aria-selected={t.id === current}
          aria-controls={panelId(t.id)}
          tabIndex={t.id === current ? 0 : -1}
          onClick={() => onChoose(t.id)}
          // The line under the chosen tab sits on the bar's own rule.
          className="-mb-px min-h-11 min-w-11 border-b-2 border-transparent text-muted -outline-offset-2 hover:text-ink aria-selected:border-ink aria-selected:font-semibold aria-selected:text-ink"
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

// A part behind the one in front stays laid out, so it keeps its scroll position and an answer
// being written carries on, but it is neither seen, read nor reached.
export function Panel({
  id,
  current,
  className,
  children,
}: {
  id: Tab;
  current: Tab;
  className: string;
  children: React.ReactNode;
}) {
  return (
    <div
      id={panelId(id)}
      data-panel={id}
      role="tabpanel"
      aria-labelledby={tabId(id)}
      inert={id !== current}
      className={`absolute inset-0 ${id === current ? "" : "invisible"} ${className}`}
    >
      {children}
    </div>
  );
}
