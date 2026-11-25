import { useLayoutEffect } from "react";
import { BUTTON_CLASS, DIMMED_BUTTON_CLASS } from "../../ask-box";

// The box for the next Query, at the foot of the conversation. Enter sends and Shift+Enter adds
// a new line. It grows with what is typed, up to a few lines.
export default function QuestionBox({
  value,
  onChange,
  onSend,
  busy,
  formRef,
  boxRef,
}: {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  // An answer is being written, which sending would cancel.
  busy: boolean;
  formRef: React.RefObject<HTMLFormElement | null>;
  boxRef: React.RefObject<HTMLTextAreaElement | null>;
}) {
  useLayoutEffect(() => {
    const box = boxRef.current;
    if (!box) return;
    box.style.height = "auto";
    box.style.height = box.scrollHeight ? `${box.scrollHeight}px` : "";
  }, [value, boxRef]);

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key !== "Enter" || e.shiftKey) return;
    // Enter that picks a word from an input method belongs to it. Safari reports the one that
    // ends a composition only by its key code.
    if (e.nativeEvent.isComposing || e.keyCode === 229) return;
    e.preventDefault();
    onSend();
  }

  return (
    <div className="shrink-0 px-4 pt-2 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
      {/* The whole box reads as the field, so it carries the focus ring and takes the click. */}
      <form
        ref={formRef}
        onSubmit={(e) => {
          e.preventDefault();
          onSend();
        }}
        onClick={(e) => {
          if (e.target === e.currentTarget) boxRef.current?.focus();
        }}
        className="mx-auto flex w-full max-w-2xl cursor-text items-end gap-2 rounded-[1.75rem] border border-muted bg-ledger py-1.5 pr-1.5 pl-5 focus-within:border-ink has-[textarea:focus-visible]:outline-2 has-[textarea:focus-visible]:outline-offset-2 has-[textarea:focus-visible]:outline-stamp"
      >
        <label htmlFor="contract-query" className="sr-only">
          Ask a question about this Contract
        </label>
        <textarea
          id="contract-query"
          ref={boxRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          rows={1}
          enterKeyHint="send"
          aria-describedby="contract-query-keys"
          placeholder="Ask in English or Hindi"
          className="scroll-area block max-h-40 min-h-11 min-w-0 flex-1 resize-none border-0 bg-transparent py-1.5 font-serif text-lg leading-relaxed text-ink placeholder:text-muted focus-visible:outline-hidden!"
        />
        <p id="contract-query-keys" className="sr-only">
          Enter sends. Shift and Enter add a new line.
        </p>
        {/* Round while it only sends; spelt out while it would also cancel an answer. */}
        <button
          type="submit"
          aria-label={busy ? undefined : "Ask"}
          title={busy ? undefined : "Ask"}
          aria-disabled={!value.trim() || undefined}
          className={`${BUTTON_CLASS} ${DIMMED_BUTTON_CLASS} aria-disabled:bg-rule! inline-flex h-11 shrink-0 cursor-pointer items-center justify-center rounded-full! ${busy ? "px-4! text-sm!" : "w-11 px-0!"}`}
        >
          {busy ? (
            "Ask this instead"
          ) : (
            <svg aria-hidden="true" viewBox="0 0 16 16" className="size-5" fill="none" stroke="currentColor" strokeWidth="1.75">
              <path d="M8 13V3.5M3.75 7.5 8 3.25l4.25 4.25" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          )}
        </button>
      </form>
    </div>
  );
}
