type ChatInputBarProps = {
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
};

export function ChatInputBar({
  value,
  disabled,
  onChange,
  onSubmit,
}: ChatInputBarProps) {
  const canSubmit = !disabled && value.trim().length >= 3;

  return (
    <div className="flex items-end gap-3 px-5 py-4">
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
        rows={2}
        className="min-h-[64px] flex-1 resize-none rounded-xl border border-[var(--border-soft)] bg-[var(--surface-muted)] px-4 py-3 text-sm leading-6 text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-[var(--focus-border)] focus:bg-white focus:ring-2 focus:ring-[var(--focus-ring)] disabled:cursor-not-allowed disabled:opacity-60"
        placeholder="Message this project..."
      />
      <button
        type="button"
        disabled={!canSubmit}
        onClick={onSubmit}
        className="h-[52px] rounded-xl bg-[var(--brand-teal)] px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-[var(--brand-teal-hover)] disabled:cursor-not-allowed disabled:opacity-60"
      >
        Send
      </button>
    </div>
  );
}
