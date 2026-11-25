import { useLayoutEffect } from "react";
import { BUTTON_CLASS, FIELD_CLASS } from "../../ask-box";

// Tells the page how tall the held box is, as --dock-height, so that the page ends above it and
// nothing focused or scrolled to is left underneath (globals.css).
function measureDock(dock: HTMLElement | null) {
  if (!dock) return;
  const root = document.documentElement;
  const apply = () => root.style.setProperty("--dock-height", `${dock.offsetHeight}px`);
  apply();
  const watch = typeof ResizeObserver === "function" ? new ResizeObserver(apply) : null;
  watch?.observe(dock);
  return () => {
    watch?.disconnect();
    root.style.removeProperty("--dock-height");
  };
}

// The box for the next Query, held at the foot of the screen. Enter sends and Shift+Enter adds
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
    // scrollHeight leaves out the border below.
    const border = box.offsetHeight - box.clientHeight;
    box.style.height = box.scrollHeight ? `${box.scrollHeight + border}px` : "";
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
    <div ref={measureDock} className="fixed inset-x-0 bottom-0 z-10 border-t border-rule bg-paper">
      <form
        ref={formRef}
        onSubmit={(e) => {
          e.preventDefault();
          onSend();
        }}
        className="mx-auto flex w-full max-w-3xl items-end gap-3 px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:px-8"
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
          placeholder="In English or Hindi"
          className={`${FIELD_CLASS} block max-h-40 min-w-0 flex-1 resize-none!`}
        />
        <p id="contract-query-keys" className="sr-only">
          Enter sends. Shift and Enter add a new line.
        </p>
        <button type="submit" className={`${BUTTON_CLASS} min-h-[3.25rem] shrink-0 px-4! sm:px-6!`}>
          {busy ? "Ask this instead" : "Ask"}
        </button>
      </form>
    </div>
  );
}
