"use client";

import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { useCallback, useEffect, useRef, useState } from "react";
import { BUTTON_CLASS, FIELD_CLASS } from "../ask-box";
import StageList, { type Stage } from "../stage-list";
import { API_URL } from "@/lib/api-url";
import type { ContractSummary, UploadedContract } from "@/lib/contract-types";
import { dailyCapMessage, retryAfterSeconds } from "@/lib/daily-cap";
import { readEvents } from "@/lib/sse";
import DeleteContract from "./delete-contract";

const ACCEPT = ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

function errorMessage(status: number | null, retryAfter: number | null = null): string {
  if (status === null)
    return "We could not reach the LegalLens service. Check your connection and try again.";
  if (status === 401) return "Your session has expired. Please sign in again, then upload your Contract.";
  if (status === 413) return "That file is too large. Please upload a smaller file.";
  if (status === 422) return "Please choose a file or paste the text of the Contract.";
  if (status === 429) return dailyCapMessage("new Contracts", "You can upload another", retryAfter);
  return "The service is unavailable right now. Please try again shortly.";
}

type Source = { kind: "file"; file: File } | { kind: "text"; text: string };
type Outcome =
  | { kind: "refused"; message: string }
  | { kind: "error"; message: string; failedStage: string | null }
  | { kind: "done"; contract: UploadedContract };

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

export default function ContractsScreen() {
  const { getToken } = useAuth();
  const [contracts, setContracts] = useState<ContractSummary[] | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [mode, setMode] = useState<"file" | "text">("file");
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [dragging, setDragging] = useState(false);
  const [running, setRunning] = useState(false);
  const [stages, setStages] = useState<Stage[]>([]);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const controller = useRef<AbortController | null>(null);

  const auth = useCallback(async (): Promise<Record<string, string>> => {
    const token = await getToken(); // fresh when the cached one is about to expire
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [getToken]);

  // Bumped to fetch the list again after an upload.
  const [reloads, setReloads] = useState(0);

  useEffect(() => {
    const ctl = new AbortController();
    (async () => {
      try {
        const res = await fetch(`${API_URL}/contracts`, { headers: await auth(), signal: ctl.signal });
        if (ctl.signal.aborted) return;
        if (!res.ok) return setListError(errorMessage(res.status));
        setContracts((await res.json()) as ContractSummary[]);
        setListError(null);
      } catch {
        if (!ctl.signal.aborted) setListError(errorMessage(null));
      }
    })();
    return () => ctl.abort();
  }, [auth, reloads]);

  useEffect(() => () => controller.current?.abort(), []);

  const source: Source | null =
    mode === "file" ? (file ? { kind: "file", file } : null) : text.trim() ? { kind: "text", text } : null;

  async function upload(src: Source) {
    controller.current?.abort();
    const ctl = new AbortController();
    controller.current = ctl;
    setRunning(true);
    setStages([]);
    setOutcome(null);
    let current: string | null = null;
    const finish = (o: Outcome) => {
      if (ctl.signal.aborted) return;
      setRunning(false);
      setOutcome(o);
    };
    try {
      const form = new FormData();
      if (src.kind === "file") form.append("file", src.file);
      else form.append("text", src.text);
      const res = await fetch(`${API_URL}/contracts/stream`, {
        method: "POST",
        headers: await auth(),
        body: form,
        signal: ctl.signal,
      });
      if (!res.ok) return finish({ kind: "error", message: errorMessage(res.status, retryAfterSeconds(res)), failedStage: null });
      if (!res.body) return finish({ kind: "error", message: errorMessage(null), failedStage: null });
      let ended = false;
      await readEvents(res.body, (name, data) => {
        if (ctl.signal.aborted) return;
        if (name === "stage") {
          current = (data as Stage).id;
          setStages((s) => [...s, data as Stage]);
        } else if (name === "answer") {
          ended = true;
          finish({ kind: "done", contract: data as UploadedContract });
          setReloads((n) => n + 1);
        } else if (name === "refusal") {
          ended = true;
          finish({ kind: "refused", message: (data as { message: string }).message });
        } else if (name === "error") {
          ended = true;
          finish({
            kind: "error",
            message: errorMessage(503),
            failedStage: (data as { stage?: string }).stage ?? current,
          });
        }
      });
      if (!ended) finish({ kind: "error", message: errorMessage(null), failedStage: current });
    } catch {
      finish({ kind: "error", message: errorMessage(null), failedStage: current });
    }
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (source && !running) void upload(source);
  }

  const tab = (id: "file" | "text", label: string) => (
    <button
      type="button"
      role="tab"
      id={`tab-${id}`}
      aria-selected={mode === id}
      aria-controls={`panel-${id}`}
      onClick={() => setMode(id)}
      className={`border-b-2 px-1 py-2 ${mode === id ? "border-ink font-semibold" : "border-transparent text-muted"}`}
    >
      {label}
    </button>
  );

  return (
    <div className="flex flex-col gap-10">
      <section aria-labelledby="upload-heading" className="flex flex-col gap-4">
        <h1 id="upload-heading" className="condensed text-3xl">
          Upload a Contract
        </h1>
        <p className="max-w-[68ch] text-muted">
          A rent agreement, a job offer, an NDA. English only, up to about 30 pages. LegalLens keeps
          the text, not the file.
        </p>
        <form onSubmit={submit} className="flex flex-col gap-4">
          <div role="tablist" aria-label="How to add the Contract" className="flex gap-6 border-b border-rule">
            {tab("file", "Upload a file")}
            {tab("text", "Paste text")}
          </div>
          {mode === "file" ? (
            <div role="tabpanel" id="panel-file" aria-labelledby="tab-file">
              <div
                data-testid="drop-zone"
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragging(false);
                  const dropped = e.dataTransfer?.files?.[0];
                  if (dropped) setFile(dropped);
                }}
                className={`flex flex-col items-start gap-3 border-2 border-dashed px-4 py-6 ${
                  dragging ? "border-ink bg-ledger" : "border-rule"
                }`}
              >
                <p>Drop a PDF or DOCX here, or</p>
                <label className="cursor-pointer underline underline-offset-4">
                  Choose a file
                  <input
                    type="file"
                    accept={ACCEPT}
                    className="sr-only"
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  />
                </label>
                {file && <p className="break-all font-medium">{file.name}</p>}
              </div>
            </div>
          ) : (
            <div role="tabpanel" id="panel-text" aria-labelledby="tab-text" className="flex flex-col gap-2">
              <label htmlFor="contract-text" className="font-medium">
                Paste the Contract
              </label>
              <textarea
                id="contract-text"
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={10}
                className={FIELD_CLASS}
              />
            </div>
          )}
          <button type="submit" disabled={!source || running} className={`${BUTTON_CLASS} self-start`}>
            {running ? "Working…" : "Upload"}
          </button>
        </form>

        {(running || (outcome?.kind === "error" && stages.length > 0)) && (
          <StageList
            stages={stages}
            loading={running}
            failedStage={outcome?.kind === "error" ? outcome.failedStage : null}
            lang="en"
          />
        )}

        {outcome?.kind === "refused" && (
          <section
            role="status"
            aria-label="Upload refused"
            className="flex max-w-[68ch] flex-col gap-2 border-l-2 border-redtape pl-4"
          >
            <h2 className="condensed text-2xl">LegalLens can&apos;t explain that</h2>
            <p className="font-serif text-lg leading-[1.7]">{outcome.message}</p>
          </section>
        )}

        {outcome?.kind === "error" && (
          <div role="alert" className="flex flex-col items-start gap-3 border-l-2 border-redtape pl-4">
            <p className="text-redtape">{outcome.message}</p>
            {source && (
              <button type="button" onClick={() => void upload(source)} className={BUTTON_CLASS}>
                Try again
              </button>
            )}
          </div>
        )}
      </section>

      <section aria-labelledby="list-heading" className="flex flex-col gap-4">
        <h2 id="list-heading" className="condensed text-2xl">
          Your Contracts
        </h2>
        {listError && (
          <p role="alert" className="text-redtape">
            {listError}
          </p>
        )}
        {!listError && contracts === null && <p className="text-muted">Loading…</p>}
        {contracts?.length === 0 && <p className="text-muted">No Contracts yet. Upload one above.</p>}
        {contracts && contracts.length > 0 && (
          <ul className="flex flex-col">
            {contracts.map((c) => (
              <li key={c.id} className="flex flex-col gap-1 border-b border-rule py-3">
                <Link href={`/contracts/${c.id}`} className="break-words text-lg font-medium underline underline-offset-4">
                  {c.title}
                </Link>
                <span className="text-sm text-muted">
                  {formatDate(c.created_at)} · {c.clause_count} {c.clause_count === 1 ? "Clause" : "Clauses"}
                </span>
                <DeleteContract
                  contractId={c.id}
                  title={c.title}
                  onDeleted={() => setContracts((list) => list && list.filter((x) => x.id !== c.id))}
                />
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
