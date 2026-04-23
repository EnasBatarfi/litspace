const actions = ["Summarize", "Compare", "Find Evidence"];

export function QuickActionsBar({
  disabled,
  onActionSelect,
}: {
  disabled: boolean;
  onActionSelect: (action: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2 border-b border-slate-100 px-5 py-3">
      {actions.map((action) => (
        <button
          key={action}
          type="button"
          disabled={disabled}
          onClick={() => onActionSelect(action)}
          className="rounded-md border border-[var(--border-soft)] bg-[var(--surface-muted)] px-3.5 py-2 text-sm font-medium text-slate-700 transition hover:border-[var(--focus-border)] hover:bg-[var(--brand-teal-soft)] hover:text-[var(--brand-ink)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {action}
        </button>
      ))}
    </div>
  );
}
