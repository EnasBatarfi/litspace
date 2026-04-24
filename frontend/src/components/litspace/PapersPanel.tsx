"use client";

import { useMemo, useState } from "react";
import type { Paper } from "@/lib/api";

function ChevronIcon({ collapsed }: { collapsed: boolean }) {
  return (
    <svg
      viewBox="0 0 16 16"
      className={["h-4 w-4 transition", collapsed ? "rotate-180" : ""].join(" ")}
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M10 4.5 6.5 8 10 11.5"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" aria-hidden="true">
      <circle cx="7" cy="7" r="4.25" stroke="currentColor" strokeWidth="1.25" />
      <path d="m10.5 10.5 3 3" stroke="currentColor" strokeLinecap="round" strokeWidth="1.25" />
    </svg>
  );
}

function StackIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" aria-hidden="true">
      <path
        d="M3.25 5.25h6.5a1 1 0 0 1 1 1v6.5a1 1 0 0 1-1 1h-6.5a1 1 0 0 1-1-1v-6.5a1 1 0 0 1 1-1Z"
        stroke="currentColor"
        strokeWidth="1.2"
      />
      <path
        d="M5.75 2.25h6.5a1 1 0 0 1 1 1v6.5"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.2"
      />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" aria-hidden="true">
      <path
        d="m4.25 4.25 7.5 7.5m0-7.5-7.5 7.5"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.25"
      />
    </svg>
  );
}

function CheckIcon({ checked }: { checked: boolean }) {
  return (
    <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" aria-hidden="true">
      <rect x="2.25" y="2.25" width="11.5" height="11.5" rx="3" stroke="currentColor" strokeWidth="1.2" />
      {checked ? (
        <path
          d="M4.75 8.25 6.9 10.4l4.35-4.55"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="1.35"
        />
      ) : null}
    </svg>
  );
}

type PapersPanelProps = {
  open: boolean;
  projectName: string | null;
  activeProjectId: number | null;
  papers: Paper[];
  activePaperId: number | null;
  selectedPaperIds: number[];
  loading: boolean;
  error: string | null;
  onToggle: () => void;
  onPaperSelect: (paperId: number) => void;
  onPaperToggleSelect: (paperId: number) => void;
  onDeletePaper: (projectId: number, paperId: number) => void;
};

function getPaperTitle(paper: Paper): string {
  return paper.title || paper.original_filename;
}

function getPaperMeta(paper: Paper): string {
  const bits = [];
  if (paper.year) {
    bits.push(String(paper.year));
  }
  if (paper.authors) {
    bits.push(paper.authors);
  }
  return bits.length > 0 ? bits.join(" • ") : paper.original_filename;
}

function getStatusLabel(status: string) {
  if (status === "indexed") {
    return "Indexed";
  }
  if (status === "processing") {
    return "Processing";
  }
  if (status === "failed") {
    return "Failed";
  }
  return status.replace(/_/g, " ");
}

function PaperCard({
  paper,
  order,
  projectId,
  active,
  selected,
  onPaperSelect,
  onPaperToggleSelect,
  onDeletePaper,
}: {
  paper: Paper;
  order: number;
  projectId: number | null;
  active: boolean;
  selected: boolean;
  onPaperSelect: (paperId: number) => void;
  onPaperToggleSelect: (paperId: number) => void;
  onDeletePaper: (projectId: number, paperId: number) => void;
}) {
  return (
    <div
      className={[
        "group flex items-start gap-2 rounded-lg border p-2 transition",
        active
          ? "border-[var(--focus-border)] bg-[var(--brand-teal-soft)] shadow-[inset_2px_0_0_var(--brand-teal)]"
          : "border-transparent bg-white hover:border-slate-200 hover:bg-slate-50",
      ].join(" ")}
    >
      <button
        type="button"
        onClick={() => onPaperToggleSelect(paper.id)}
        aria-pressed={selected}
        aria-label={
          selected
            ? `Remove ${getPaperTitle(paper)} from selected context papers`
            : `Select ${getPaperTitle(paper)} as a context hint`
        }
        title={selected ? "Remove from selected papers" : "Select as a context hint"}
        className={[
          "mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-md border transition",
          selected
            ? "border-[var(--brand-teal)] bg-[var(--brand-teal-soft)] text-[var(--brand-teal)]"
            : "border-slate-200 bg-white text-slate-400 hover:border-[var(--focus-border)] hover:bg-white hover:text-slate-700",
        ].join(" ")}
      >
        <CheckIcon checked={selected} />
      </button>

      <button
        type="button"
        onClick={() => onPaperSelect(paper.id)}
        className="flex min-w-0 flex-1 items-start gap-3 text-left"
      >
        <span
          className={[
            "mt-0.5 inline-flex h-8 min-w-[32px] items-center justify-center rounded-full px-2 text-xs font-semibold",
            "bg-slate-100 text-slate-500",
          ].join(" ")}
          aria-label={`Paper ${order}`}
        >
          {order}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-semibold leading-5 text-slate-900">
            {getPaperTitle(paper)}
          </span>
          <span className="mt-1 block truncate text-xs text-slate-500">{getPaperMeta(paper)}</span>
          <span className="mt-2 flex flex-wrap items-center gap-2">
            <span className="inline-flex rounded-md bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-600">
              {getStatusLabel(paper.status)}
            </span>
          </span>
        </span>
      </button>

      <div className="mt-1 flex shrink-0 items-center">
        <button
          type="button"
          onClick={() => {
            if (projectId) {
              onDeletePaper(projectId, paper.id);
            }
          }}
          aria-label={`Delete paper ${getPaperTitle(paper)}`}
          className="flex h-8 w-8 items-center justify-center rounded-md text-slate-400 opacity-0 transition hover:bg-white hover:text-rose-600 group-hover:opacity-100"
        >
          <CloseIcon />
        </button>
      </div>
    </div>
  );
}

export function PapersPanel({
  open,
  projectName,
  activeProjectId,
  papers,
  activePaperId,
  selectedPaperIds,
  loading,
  error,
  onToggle,
  onPaperSelect,
  onPaperToggleSelect,
  onDeletePaper,
}: PapersPanelProps) {
  const [query, setQuery] = useState("");
  const selectedPaperIdSet = useMemo(() => new Set(selectedPaperIds), [selectedPaperIds]);
  const indexedCount = useMemo(
    () => papers.filter((paper) => paper.status === "indexed").length,
    [papers],
  );
  const paperOrderById = useMemo(
    () => new Map(papers.map((paper, index) => [paper.id, index + 1])),
    [papers],
  );

  const filteredPapers = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return papers;
    }

    return papers.filter((paper) => {
      const haystack = [
        paper.title,
        paper.original_filename,
        paper.authors,
        paper.year ? String(paper.year) : null,
        paper.status,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return haystack.includes(normalized);
    });
  }, [papers, query]);

  if (!open) {
    return (
      <aside className="flex h-full w-16 shrink-0 items-start justify-center border-r border-[var(--border-soft)] bg-[var(--surface-rail)] px-2 pt-4">
        <button
          type="button"
          onClick={onToggle}
          className="flex w-full flex-col items-center gap-2 rounded-xl px-2 py-3 text-slate-500 transition hover:bg-white/70 hover:text-slate-700"
          aria-label="Expand papers panel"
        >
          <span className="relative flex h-10 w-10 items-center justify-center rounded-xl border border-[var(--border-soft)] bg-white text-[var(--brand-ink)] shadow-sm">
            <StackIcon />
            {papers.length > 0 ? (
              <span className="absolute -right-1 -top-1 flex h-5 min-w-[20px] items-center justify-center rounded-full bg-[var(--brand-teal)] px-1 text-[10px] font-semibold text-white">
                {papers.length}
              </span>
            ) : null}
          </span>
          <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-400">
            Papers
          </span>
        </button>
      </aside>
    );
  }

  return (
    <aside className="flex h-full w-[316px] shrink-0 flex-col border-r border-[var(--border-soft)] bg-[var(--surface-rail)]">
      <div className="border-b border-slate-200 px-5 py-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-slate-950">Papers</h2>
              <span className="text-xs font-medium text-slate-400">
                {indexedCount}/{papers.length || 0} indexed
              </span>
            </div>
            <p className="mt-1 text-sm text-slate-500">Documents shared across chats</p>
          </div>
          <div className="flex items-center">
            <button
              type="button"
              onClick={onToggle}
              className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-slate-500 transition hover:bg-slate-200 hover:text-slate-900"
              aria-label="Collapse papers panel"
            >
              <ChevronIcon collapsed={false} />
            </button>
          </div>
        </div>

        <label className="mt-4 flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-500 shadow-sm">
          <SearchIcon />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            disabled={!projectName}
            className="min-w-0 flex-1 bg-transparent text-sm text-slate-700 outline-none placeholder:text-slate-400 disabled:cursor-not-allowed"
            placeholder="Search papers..."
          />
        </label>

        <p className="mt-4 text-xs text-slate-500">
          {filteredPapers.length === papers.length
            ? `${papers.length} papers`
            : `${filteredPapers.length} of ${papers.length} papers`}
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {!projectName ? (
          <p className="rounded-lg border border-slate-200 bg-white px-4 py-5 text-sm leading-6 text-slate-500 shadow-sm">
            Create or select a project to manage its documents.
          </p>
        ) : loading ? (
          <p className="rounded-lg border border-slate-200 bg-white px-4 py-5 text-sm text-slate-500 shadow-sm">
            Loading project papers...
          </p>
        ) : error ? (
          <p className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-5 text-sm text-rose-700">
            {error}
          </p>
        ) : filteredPapers.length > 0 ? (
          <div className="space-y-2">
            {filteredPapers.map((paper) => (
              <PaperCard
                key={paper.id}
                paper={paper}
                order={paperOrderById.get(paper.id) || 0}
                projectId={activeProjectId}
                active={paper.id === activePaperId}
                selected={selectedPaperIdSet.has(paper.id)}
                onPaperSelect={onPaperSelect}
                onPaperToggleSelect={onPaperToggleSelect}
                onDeletePaper={onDeletePaper}
              />
            ))}
          </div>
        ) : papers.length > 0 ? (
          <p className="rounded-lg border border-slate-200 bg-white px-4 py-5 text-sm leading-6 text-slate-500 shadow-sm">
            No papers match this search.
          </p>
        ) : (
          <p className="rounded-lg border border-slate-200 bg-white px-4 py-5 text-sm leading-6 text-slate-500 shadow-sm">
            No papers uploaded yet. Add PDFs to make this project queryable.
          </p>
        )}
      </div>
    </aside>
  );
}
