const actions = ["Summarize", "Compare", "Find Evidence"];

export function QuickActionsBar({
  disabled,
  onActionSelect,
}: {
  disabled: boolean;
  onActionSelect: (action: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2 px-5 pt-4">
      {actions.map((action) => (
        <button
          key={action}
          type="button"
          disabled={disabled}
          onClick={() => onActionSelect(action)}
          className="rounded-full border border-slate-200 bg-white px-3.5 py-1.5 text-[13px] font-medium text-slate-600 transition hover:border-[var(--focus-border)] hover:bg-[var(--brand-teal-soft)] hover:text-[var(--brand-ink)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {action}
        </button>
      ))}
    </div>
  );
}
