export type Stage = { id: string; label: string };

// The Stages of a request as they happen: done, the one in progress, and the one that
// failed. Shared by the asking screen and the Contract upload.
export default function StageList({
  stages,
  loading,
  failedStage,
  lang,
}: {
  stages: Stage[];
  loading: boolean;
  failedStage: string | null;
  lang: string;
}) {
  return (
    <div role="status" aria-label="Progress">
      {stages.length === 0 && <p className="text-muted">Starting…</p>}
      <ol className="flex flex-col gap-2.5 border-l border-rule">
        {stages.map((stage, i) => {
          const last = i === stages.length - 1;
          const failed = !loading && last && failedStage !== null;
          const active = loading && last;
          return (
            <li
              key={stage.id}
              className={`-ml-[5px] flex items-center gap-3 ${
                failed ? "font-medium text-redtape" : active ? "font-medium text-ink" : "text-muted"
              }`}
              aria-current={active ? "step" : undefined}
            >
              <span
                aria-hidden="true"
                className={`size-[9px] shrink-0 rounded-full ${
                  failed ? "bg-redtape" : active ? "stage-pulse bg-ink" : "bg-stamp"
                }`}
              />
              <span lang={lang}>{stage.label}</span>
              <span className="sr-only"> ({failed ? "failed" : active ? "in progress" : "done"})</span>
              {failed && <span aria-hidden="true" className="text-sm">failed</span>}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
