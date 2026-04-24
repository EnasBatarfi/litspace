type ChatInputBarProps = {
  value: string;
  placeholder: string;
  disabled: boolean;
  validationMessage?: string | null;
  onChange: (value: string) => void;
  onSubmit: () => void;
};

function SendIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" aria-hidden="true">
      <path
        d="M8 12.75v-8.5M4.75 7.5 8 4.25 11.25 7.5"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.6"
      />
    </svg>
  );
}

export function ChatInputBar({
  value,
  placeholder,
  disabled,
  validationMessage,
  onChange,
  onSubmit,
}: ChatInputBarProps) {
  const canSubmit = !disabled && value.trim().length >= 1 && !validationMessage;

  return (
    <div className="px-5 pb-5 pt-3">
      <div className="relative rounded-3xl border border-slate-300 bg-white shadow-[0_14px_36px_rgba(15,23,42,0.08)] transition focus-within:border-[var(--focus-border)] focus-within:ring-2 focus-within:ring-[var(--focus-ring)]">
        <div className="pointer-events-none absolute left-6 top-4 text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-400">
          Ask the project
        </div>
        <textarea
          value={value}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              if (canSubmit) {
                onSubmit();
              }
            }
          }}
          rows={3}
          className="min-h-[120px] w-full resize-none bg-transparent px-6 pb-5 pt-10 pr-20 text-[15px] leading-7 text-slate-800 outline-none transition placeholder:text-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
          placeholder={placeholder}
        />
        <button
          type="button"
          disabled={!canSubmit}
          onClick={onSubmit}
          className="absolute bottom-4 right-4 flex h-11 w-11 items-center justify-center rounded-full bg-[var(--brand-teal)] text-white shadow-[0_8px_18px_rgba(20,120,98,0.25)] transition hover:bg-[var(--brand-teal-hover)] disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-white/80"
          aria-label="Send message"
        >
          <SendIcon />
        </button>
      </div>
      {validationMessage ? (
        <p className="px-2 pt-2 text-sm text-rose-600">{validationMessage}</p>
      ) : null}
    </div>
  );
}
