"use client";

import { useEffect, useState } from "react";
import type { CreateProjectPayload } from "@/lib/api";

type CreateProjectModalProps = {
  open: boolean;
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (payload: CreateProjectPayload) => Promise<void> | void;
};

const EMPTY_FORM = {
  name: "",
  topicLabel: "",
  description: "",
};

export function CreateProjectModal({
  open,
  loading,
  error,
  onClose,
  onSubmit,
}: CreateProjectModalProps) {
  const [form, setForm] = useState(EMPTY_FORM);

  useEffect(() => {
    if (!open) {
      setForm(EMPTY_FORM);
    }
  }, [open]);

  if (!open) {
    return null;
  }

  const canSubmit = form.name.trim().length >= 2 && !loading;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-4 backdrop-blur-sm">
      <div className="w-full max-w-[520px] rounded-lg border border-slate-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.22)]">
        <div className="border-b border-slate-200 px-6 py-5">
          <h2 className="text-xl font-semibold text-slate-950">Create project</h2>
          <p className="mt-1 text-sm leading-6 text-slate-500">
            Each project gets its own chats and shared paper collection.
          </p>
        </div>

        <form
          className="space-y-5 px-6 py-6"
          onSubmit={async (event) => {
            event.preventDefault();
            if (!canSubmit) {
              return;
            }

            await onSubmit({
              name: form.name.trim(),
              topic_label: form.topicLabel.trim() || null,
              description: form.description.trim() || null,
            });
          }}
        >
          <label className="block">
            <span className="mb-2 block text-sm font-semibold text-slate-800">Project name</span>
            <input
              autoFocus
              value={form.name}
              onChange={(event) =>
                setForm((current) => ({ ...current, name: event.target.value }))
              }
              className="w-full rounded-md border border-[var(--border-soft)] bg-[var(--surface-muted)] px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-[var(--focus-border)] focus:bg-white focus:ring-2 focus:ring-[var(--focus-ring)]"
              placeholder="AI Safety Reading Group"
            />
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-semibold text-slate-800">Topic label</span>
            <input
              value={form.topicLabel}
              onChange={(event) =>
                setForm((current) => ({ ...current, topicLabel: event.target.value }))
              }
              className="w-full rounded-md border border-[var(--border-soft)] bg-[var(--surface-muted)] px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-[var(--focus-border)] focus:bg-white focus:ring-2 focus:ring-[var(--focus-ring)]"
              placeholder="LLM Safety"
            />
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-semibold text-slate-800">Description</span>
            <textarea
              rows={4}
              value={form.description}
              onChange={(event) =>
                setForm((current) => ({ ...current, description: event.target.value }))
              }
              className="w-full resize-none rounded-md border border-[var(--border-soft)] bg-[var(--surface-muted)] px-4 py-3 text-sm leading-6 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-[var(--focus-border)] focus:bg-white focus:ring-2 focus:ring-[var(--focus-ring)]"
              placeholder="Grounded Q&A workspace for project papers, experiments, and notes."
            />
          </label>

          {error ? (
            <p className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </p>
          ) : null}

          <div className="flex items-center justify-end gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="rounded-md border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!canSubmit}
              className="rounded-md bg-[var(--brand-teal)] px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[var(--brand-teal-hover)] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Creating..." : "Create Project"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
