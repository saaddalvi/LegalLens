"use client";

import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { useCallback, useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { BUSY_BUTTON_CLASS, BUTTON_CLASS, DIMMED_BUTTON_CLASS, FIELD_CLASS } from "../ask-box";
import StageList, { type Stage } from "../stage-list";
import { API_URL } from "@/lib/api-url";
import type { ContractSummary, UploadedContract } from "@/lib/contract-types";
import { dailyCapMessage, isDailyCap, retryAfterSeconds } from "@/lib/daily-cap";
import { readEvents } from "@/lib/sse";
import DeleteContract from "./delete-contract";
import { takeDeleted } from "./deleted-notice";
import SignInAgain, { sessionMessage } from "./sign-in-again";

const FILE_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];
const ACCEPT = [".pdf", ".docx", ...FILE_TYPES].join(",");

// The backend's MAX_UPLOAD_BYTES.
const MB = 1024 * 1024;
const MAX_UPLOAD_MB = 20;

const UPLOAD_TERMS = [
  [
    "You get",
    "A Contract brief: parties, purpose, key terms, what each party must do, and any Flagged clauses found to differ from Indian law. Then ask questions in English or Hindi. LegalLens won't tell you whether to sign.",
  ],
  [
    "LegalLens keeps",
    "The Contract's text, its brief, and your questions and answers, until you delete the Contract. Your file is not kept.",
  ],
  [
    "Google receives",
    "Your Contract and questions go to Google's Gemini AI. On its free tier, Google may use them to improve its products, and human reviewers may read them. Remove ID numbers, phone numbers and other personal details first.",
  ],
];

const RUNNING_NOTE =
  "Keep this tab open until your brief is ready. Cancelling or closing the tab stops the upload, and it may still count towards today's limit.";

// What went wrong with a request, by what the user can do about it.
// A "file" problem is with the chosen file, and is shown in the file picker.
type Problem = "retry" | "session" | "daily_cap" | "file" | "other";
type Failure = { problem: Problem; message: string };

const UNREACHABLE: Failure = {
  problem: "retry",
  message: "We could not reach the LegalLens service. Check your connection and try again.",
};
const UNAVAILABLE: Failure = {
  problem: "retry",
  message: "The service is unavailable right now. Please try again shortly.",
};

function tooLarge(bytes?: number): Failure {
  // Rounded up, so a file just over the limit never reads as being at it.
  const size = bytes === undefined ? "too large" : `${Math.ceil((bytes / MB) * 10) / 10} MB`;
  return { problem: "file", message: `That file is ${size}. The limit is ${MAX_UPLOAD_MB} MB.` };
}

// Why a file cannot be sent, if it cannot. The name or the type will do, as some phones
// leave one of them out; the service itself reads the file's first bytes.
function fileFailure(file: File): Failure | null {
  if (!/\.(pdf|docx)$/i.test(file.name) && !FILE_TYPES.includes(file.type))
    return { problem: "file", message: `${file.name} is not a PDF or DOCX file.` };
  if (file.size === 0) return { problem: "file", message: `${file.name} is empty.` };
  if (file.size > MAX_UPLOAD_MB * MB) return tooLarge(file.size);
  return null;
}

// A refused request. The message for a 401 is written when shown, as it depends on the session.
function failureFor(res: Response, sent?: Source["kind"]): Failure {
  if (res.status === 401) return { problem: "session", message: "" };
  if (res.status === 413)
    return sent === "text" ? { problem: "other", message: "That text is too large to upload." } : tooLarge();
  if (res.status === 422)
    return { problem: "other", message: "Please choose a file or paste the text of the Contract." };
  if (res.status === 429 && isDailyCap(res))
    return {
      problem: "daily_cap",
      message: dailyCapMessage("new Contracts", "You can upload another", retryAfterSeconds(res)),
    };
  if (res.status === 429)
    return { problem: "retry", message: "Too many requests just now. Please wait a minute and try again." };
  return UNAVAILABLE;
}

type Mode = "file" | "text";
type Source = { kind: "file"; file: File } | { kind: "text"; text: string };
type Outcome =
  | { kind: "refused"; message: string }
  | ({ kind: "error"; failedStage: string | null } & Failure)
  | { kind: "done"; contract: UploadedContract };

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

export default function ContractsScreen() {
  const { getToken, isSignedIn } = useAuth();
  const [contracts, setContracts] = useState<ContractSummary[] | null>(null);
  const [listError, setListError] = useState<Failure | null>(null);
  const [mode, setMode] = useState<Mode>("file");
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [dragging, setDragging] = useState(false);
  const [running, setRunning] = useState(false);
  const [stages, setStages] = useState<Stage[]>([]);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  // Shown beside the button: what is missing, or that an upload was cancelled.
  const [hint, setHint] = useState("");
  // Read out by a screen reader where the change on screen speaks for itself.
  const [announcement, setAnnouncement] = useState("");
  const controller = useRef<AbortController | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const textField = useRef<HTMLTextAreaElement>(null);
  const submitButton = useRef<HTMLButtonElement>(null);
  const readyBlock = useRef<HTMLElement>(null);
  const listHeading = useRef<HTMLHeadingElement>(null);

  // `fresh` skips Clerk's cache, for a token the service has just refused.
  const auth = useCallback(
    async (fresh = false): Promise<Record<string, string>> => {
      // Otherwise Clerk hands back a fresh token when the cached one is about to expire.
      const token = await getToken(fresh ? { skipCache: true } : undefined);
      return token ? { Authorization: `Bearer ${token}` } : {};
    },
    [getToken],
  );

  // Bumped to fetch the list again.
  const [reloads, setReloads] = useState(0);
  const reload = () => setReloads((n) => n + 1);

  useEffect(() => {
    const ctl = new AbortController();
    (async () => {
      try {
        const res = await fetch(`${API_URL}/contracts`, { headers: await auth(), signal: ctl.signal });
        if (ctl.signal.aborted) return;
        if (!res.ok) return setListError(res.status === 401 ? failureFor(res) : UNAVAILABLE);
        setContracts((await res.json()) as ContractSummary[]);
        setListError(null);
      } catch {
        if (!ctl.signal.aborted) setListError(UNREACHABLE);
      }
    })();
    return () => ctl.abort();
    // isSignedIn: signing in again fetches the list that was refused.
  }, [auth, reloads, isSignedIn]);

  // A Contract deleted on its own page: say so here, where the user lands.
  useEffect(() => {
    const gone = takeDeleted();
    if (!gone) return;
    listHeading.current?.focus();
    forget(gone.id, gone.title);
  }, []);

  // The ready block takes focus once, not again each time the user returns to this page.
  const readyId = outcome?.kind === "done" ? outcome.contract.id : null;
  const focusedId = useRef<string | null>(null);
  useEffect(() => {
    if (!readyId || focusedId.current === readyId) return;
    focusedId.current = readyId;
    readyBlock.current?.focus();
  }, [readyId]);

  function forget(id: string, title: string) {
    setContracts((list) => list && list.filter((c) => c.id !== id));
    setOutcome((o) => (o?.kind === "done" && o.contract.id === id ? null : o));
    setAnnouncement(`Deleted ${title}.`);
  }

  // A row deleted from the list. Focus moves to a neighbour if the user is still on that row.
  function removed(c: ContractSummary) {
    const row = document.getElementById(`contract-${c.id}`);
    const active = document.activeElement;
    if (row && (active === document.body || row.contains(active))) {
      const neighbour = row.nextElementSibling ?? row.previousElementSibling;
      (neighbour?.querySelector("a") ?? listHeading.current)?.focus();
    }
    forget(c.id, c.title);
  }

  const source: Source | null =
    mode === "file" ? (file ? { kind: "file", file } : null) : text.trim() ? { kind: "text", text } : null;

  // Whatever was said about the last attempt no longer applies to what is in the form.
  function clearLast() {
    setHint("");
    setAnnouncement("");
    setStages([]);
    setOutcome(null);
  }

  function clearFile() {
    setFile(null);
    // Without this, choosing the same file again would not count as a change.
    if (fileInput.current) fileInput.current.value = "";
  }

  function choose(next: File | null) {
    if (running) return;
    clearLast();
    const failure = next && fileFailure(next);
    if (failure) {
      clearFile();
      setOutcome({ kind: "error", failedStage: null, ...failure });
    } else setFile(next);
  }

  // The Remove button goes away, so focus moves to the file input.
  function removeFile(name: string) {
    clearLast();
    clearFile();
    setAnnouncement(`Removed ${name}.`);
    fileInput.current?.focus();
  }

  function changeMode(next: Mode) {
    setMode(next);
    if (!running) clearLast();
  }

  // The upload carries on if the user moves to another page in the app: nothing here aborts it
  // then. Only closing or reloading the tab would stop it, so the browser asks first.
  async function upload(src: Source, freshToken = false) {
    controller.current?.abort();
    const ctl = new AbortController();
    controller.current = ctl;
    const warn = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = ""; // older browsers ask only when this is set
    };
    const stopWarning = () => window.removeEventListener("beforeunload", warn);
    window.addEventListener("beforeunload", warn);
    ctl.signal.addEventListener("abort", stopWarning);
    clearLast();
    setRunning(true);
    let current: string | null = null;
    const finish = (o: Outcome) => {
      if (ctl.signal.aborted) return;
      stopWarning();
      setRunning(false);
      setOutcome(o);
    };
    const fail = (failure: Failure, failedStage: string | null = current) =>
      finish({ kind: "error", failedStage, ...failure });
    // The connection dropped. The Contract may have been saved all the same, so look.
    const lost = () => {
      if (ctl.signal.aborted) return;
      fail(UNREACHABLE);
      reload();
    };
    try {
      const form = new FormData();
      if (src.kind === "file") form.append("file", src.file);
      else form.append("text", src.text);
      const res = await fetch(`${API_URL}/contracts/stream`, {
        method: "POST",
        headers: await auth(freshToken),
        body: form,
        signal: ctl.signal,
      });
      if (!res.ok) {
        if (res.status === 413 && !ctl.signal.aborted) clearFile();
        return fail(failureFor(res, src.kind));
      }
      if (!res.body) return lost();
      let ended = false;
      await readEvents(res.body, (name, data) => {
        if (ctl.signal.aborted) return;
        if (name === "stage") {
          current = (data as Stage).id;
          setStages((s) => [...s, data as Stage]);
        } else if (name === "answer") {
          ended = true;
          finish({ kind: "done", contract: data as UploadedContract });
          clearFile();
          setText("");
          setAnnouncement("Your Contract brief is ready.");
          reload();
        } else if (name === "refusal") {
          ended = true;
          const { message } = data as { message: string };
          finish({ kind: "refused", message });
          setAnnouncement(`LegalLens can't explain that. ${message}`);
        } else if (name === "error") {
          ended = true;
          fail(UNAVAILABLE, (data as { stage?: string }).stage ?? current);
        }
      });
      if (!ended) lost();
    } catch {
      lost();
    }
  }

  // The buttons pressed here go away, so focus moves to the one that stays.
  function cancel() {
    controller.current?.abort();
    setRunning(false);
    setStages([]);
    setHint("Upload cancelled. It may still count towards today's limit.");
    submitButton.current?.focus();
    reload();
  }

  function tryAgain(fresh: boolean) {
    if (!source) return;
    submitButton.current?.focus();
    void upload(source, fresh);
  }

  function pasteInstead() {
    flushSync(() => changeMode("text"));
    textField.current?.focus();
  }

  function reloadList() {
    listHeading.current?.focus();
    setListError(null);
    reload();
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    // The button stays focusable while it looks disabled, so it is checked here.
    if (running) return;
    if (source) return void upload(source);
    setHint(mode === "file" ? "Choose a file first." : "Paste the Contract first.");
    (mode === "file" ? fileInput : textField).current?.focus();
  }

  const fileProblem =
    mode === "file" && outcome?.kind === "error" && outcome.problem === "file" ? outcome.message : "";
  // With no file there is nothing to upload, so choosing one is the main action.
  const awaitingFile = mode === "file" && !file;

  const modeChoice = (value: Mode, label: string) => (
    <label className={`flex min-h-11 cursor-pointer items-center gap-2 ${mode === value ? "font-semibold" : "text-muted"}`}>
      <input
        type="radio"
        name="contract-source"
        value={value}
        checked={mode === value}
        onChange={() => changeMode(value)}
        className="size-4 accent-ink"
      />
      {label}
    </label>
  );

  return (
    <div className="relative flex flex-col gap-10">
      <section aria-labelledby="upload-heading" className="flex flex-col gap-4">
        <h1 id="upload-heading" className="condensed text-3xl">
          Upload a Contract
        </h1>
        <p className="max-w-[68ch] text-muted">
          A rent agreement, a job offer, an NDA. English only, up to about 30 pages.
        </p>
        {/* What the user should know before sending a Contract. The Google row describes the
            free tier of Gemini: revisit it if the deployed key gets billing. */}
        <dl className="border-t border-rule">
          {UPLOAD_TERMS.map(([term, detail]) => (
            <div key={term} className="grid gap-x-4 gap-y-1 border-b border-rule py-3 sm:grid-cols-[10rem_1fr]">
              <dt className="font-semibold">{term}</dt>
              <dd className="max-w-[68ch]">{detail}</dd>
            </div>
          ))}
        </dl>
        <form onSubmit={submit} className="flex flex-col gap-4">
          <fieldset className="flex flex-wrap gap-x-6 border-b border-rule pb-1">
            <legend className="sr-only">How to add the Contract</legend>
            {modeChoice("file", "Upload a file")}
            {modeChoice("text", "Paste text")}
          </fieldset>
          {mode === "file" ? (
            // The box is drawn only for a mouse, which can drag a file onto it.
            <div
              data-testid="drop-zone"
              onDragOver={(e) => {
                e.preventDefault();
                if (!running) setDragging(true);
              }}
              onDragLeave={(e) => {
                // Passing over the box's own contents is not leaving it.
                if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setDragging(false);
              }}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                const dropped = e.dataTransfer?.files?.[0];
                if (dropped) choose(dropped);
              }}
              className={`flex flex-col items-start gap-3 mouse:border-2 mouse:border-dashed mouse:px-4 mouse:py-6 ${
                dragging ? "border-ink bg-ledger" : "border-rule"
              }`}
            >
              {file && (
                <p id="chosen-file" className="text-lg font-medium wrap-anywhere">
                  {file.name}
                </p>
              )}
              {fileProblem && (
                <p id="file-problem" role="alert" className="text-redtape wrap-anywhere">
                  {fileProblem}
                </p>
              )}
              <div className="flex w-full flex-wrap items-center gap-x-6 gap-y-2">
                {/* The input is visually hidden, so the label draws its focus ring. */}
                <label
                  className={`relative inline-flex min-h-11 items-center justify-center has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-3 has-[:focus-visible]:outline-stamp ${
                    file
                      ? `rounded underline underline-offset-4 ${running ? "text-muted" : "cursor-pointer"}`
                      : `w-full sm:w-auto ${BUTTON_CLASS} ${running ? "bg-ledger! text-muted!" : "cursor-pointer"}`
                  }`}
                >
                  {file ? "Choose another file" : "Choose a file"}
                  <input
                    ref={fileInput}
                    type="file"
                    accept={ACCEPT}
                    className="sr-only"
                    aria-disabled={running || undefined}
                    aria-invalid={fileProblem ? true : undefined}
                    aria-describedby={file ? "chosen-file" : fileProblem ? "file-problem" : "file-limits"}
                    onClick={(e) => {
                      if (running) e.preventDefault();
                    }}
                    onChange={(e) => choose(e.target.files?.[0] ?? null)}
                  />
                </label>
                {file && !running && (
                  <button
                    type="button"
                    onClick={() => removeFile(file.name)}
                    aria-describedby="chosen-file"
                    className="min-h-11 min-w-11 underline underline-offset-4"
                  >
                    Remove
                  </button>
                )}
                {fileProblem && (
                  <button type="button" onClick={pasteInstead} className="min-h-11 underline underline-offset-4">
                    Paste the text instead
                  </button>
                )}
              </div>
              {!file && (
                <p id="file-limits" className="text-sm text-muted">
                  PDF or DOCX, up to {MAX_UPLOAD_MB} MB.
                  <span className="hidden mouse:inline"> You can also drag a file into this box.</span>
                </p>
              )}
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              <label htmlFor="contract-text" className="font-medium">
                Paste the Contract
              </label>
              <textarea
                id="contract-text"
                ref={textField}
                value={text}
                onChange={(e) => {
                  clearLast();
                  setText(e.target.value);
                }}
                readOnly={running}
                rows={10}
                className={FIELD_CLASS}
              />
            </div>
          )}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <button
              ref={submitButton}
              type="submit"
              aria-disabled={running || awaitingFile || undefined}
              className={`${BUTTON_CLASS} ${running ? BUSY_BUTTON_CLASS : DIMMED_BUTTON_CLASS}`}
            >
              {running ? "Working…" : "Upload"}
            </button>
            {running && (
              <button type="button" onClick={cancel} className="min-h-11 underline underline-offset-4">
                Cancel upload
              </button>
            )}
          </div>
          {/* Always in the page so a screen reader announces the text when it appears. */}
          <p role="status" className={`max-w-[68ch] empty:-mt-4 ${running ? "text-sm text-muted" : "font-medium"}`}>
            {running ? RUNNING_NOTE : hint}
          </p>
        </form>

        <p role="status" className="sr-only">
          {announcement}
        </p>

        {(running || (outcome?.kind === "error" && stages.length > 0)) && (
          <StageList
            stages={stages}
            loading={running}
            failedStage={outcome?.kind === "error" ? outcome.failedStage : null}
            lang="en"
          />
        )}

        {outcome?.kind === "done" && (
          <section
            ref={readyBlock}
            tabIndex={-1}
            aria-labelledby="ready-heading"
            aria-describedby="ready-title"
            className="flex max-w-[68ch] flex-col items-start gap-3 rounded border border-ink bg-ledger px-4 py-4"
          >
            <h2 id="ready-heading" className="condensed text-2xl">
              Your Contract brief is ready
            </h2>
            <p id="ready-title" className="break-words">
              {outcome.contract.title}
            </p>
            <Link href={`/contracts/${outcome.contract.id}`} className={`${BUTTON_CLASS} inline-block`}>
              Read the Contract brief
            </Link>
          </section>
        )}

        {outcome?.kind === "refused" && (
          <section
            aria-label="Upload refused"
            className="flex max-w-[68ch] flex-col gap-2 border-l-2 border-redtape pl-4"
          >
            <h2 className="condensed text-2xl">LegalLens can&apos;t explain that</h2>
            <p className="font-serif text-lg leading-[1.7]">{outcome.message}</p>
          </section>
        )}

        {outcome?.kind === "error" && !fileProblem && (
          <div role="alert" className="flex flex-col items-start gap-3 border-l-2 border-redtape pl-4">
            <p className="text-redtape">
              {outcome.problem === "session"
                ? sessionMessage(isSignedIn, "upload your Contract")
                : outcome.message}
            </p>
            {outcome.problem === "session" && isSignedIn === false ? (
              <SignInAgain />
            ) : outcome.problem === "retry" || outcome.problem === "session" ? (
              source && (
                <button
                  type="button"
                  onClick={() => tryAgain(outcome.problem === "session")}
                  className={BUTTON_CLASS}
                >
                  Try again
                </button>
              )
            ) : outcome.problem === "daily_cap" ? (
              contracts?.length ? (
                <button type="button" onClick={() => listHeading.current?.focus()} className={BUTTON_CLASS}>
                  Go to your Contracts
                </button>
              ) : (
                <Link href="/ask" className={`${BUTTON_CLASS} inline-block`}>
                  Ask a question instead
                </Link>
              )
            ) : null}
          </div>
        )}
      </section>

      {/* On wide screens the list stands in the empty margin left of the page column and
          stays in view as the page scrolls. It comes after the upload in reading order. */}
      <section aria-labelledby="list-heading" className="xl:absolute xl:inset-y-0 xl:right-full xl:mr-8 xl:w-56 2xl:mr-12 2xl:w-72">
        {/* The padding keeps focus rings from being clipped by the scrolling box. */}
        <div className="flex flex-col gap-4 xl:sticky xl:top-2 xl:-m-2 xl:max-h-[calc(100dvh-1rem)] xl:overflow-y-auto xl:p-2">
          <h2 id="list-heading" ref={listHeading} tabIndex={-1} className="condensed self-start text-2xl">
            Your Contracts
          </h2>
          {listError && (
            <div role="alert" className="flex flex-col items-start gap-3">
              <p className="text-redtape">
                {listError.problem === "session"
                  ? sessionMessage(isSignedIn, "see your Contracts")
                  : listError.message}
              </p>
              {listError.problem === "session" && isSignedIn === false ? (
                <SignInAgain />
              ) : (
                <button type="button" onClick={reloadList} className={BUTTON_CLASS}>
                  Try loading again
                </button>
              )}
            </div>
          )}
          {!listError && contracts === null && <p className="text-muted">Loading…</p>}
          {contracts?.length === 0 && <p className="text-muted">No Contracts yet.<span className="xl:hidden"> Upload one above.</span></p>}
          {contracts && contracts.length > 0 && (
            <ul className="flex flex-col">
              {contracts.map((c) => (
                <li key={c.id} id={`contract-${c.id}`} className="flex flex-col gap-1 border-b border-rule py-3">
                  <Link href={`/contracts/${c.id}`} className="break-words text-lg font-medium underline underline-offset-4">
                    {c.title}
                  </Link>
                  <span className="text-sm text-muted">
                    {formatDate(c.created_at)} · {c.clause_count} {c.clause_count === 1 ? "Clause" : "Clauses"}
                  </span>
                  <DeleteContract
                    contractId={c.id}
                    title={c.title}
                    onDeleted={() => removed(c)}
                  />
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}
