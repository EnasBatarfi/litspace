"use client";

import { useEffect, useRef } from "react";
import type { AnswerSource } from "@/lib/api";

function ChevronIcon({ collapsed }: { collapsed: boolean }) {
  return (
    <svg
      viewBox="0 0 16 16"
      className={["h-4 w-4 transition", collapsed ? "rotate-180" : ""].join(" ")}
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M6 4.5 9.5 8 6 11.5"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
    </svg>
  );
}

type SourcesPanelProps = {
  open: boolean;
  sources: AnswerSource[];
  activeSourceId: string | null;
  onClose: () => void;
  onOpen: () => void;
  onSourceSelect: (sourceId: string) => void;
};

function QuoteIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" aria-hidden="true">
      <path
        d="M5 6.25A2.75 2.75 0 0 0 2.25 9v2.75h4.5V9H5.5a1.25 1.25 0 0 1 1.25-1.25V6.25ZM12.5 6.25A2.75 2.75 0 0 0 9.75 9v2.75h4.5V9H13a1.25 1.25 0 0 1 1.25-1.25V6.25Z"
        stroke="currentColor"
        strokeLinejoin="round"
        strokeWidth="1.2"
      />
    </svg>
  );
}

function getRelevanceLabel(index: number) {
  if (index <= 1) {
    return "High relevance";
  }
  if (index <= 3) {
    return "Medium relevance";
  }
  return "Low relevance";
}

function SourceCard({
  source,
  index,
  active,
  onSourceSelect,
}: {
  source: AnswerSource;
  index: number;
  active: boolean;
  onSourceSelect: (sourceId: string) => void;
}) {
  const paperLabel = source.paper_title || source.original_filename || `Paper ${source.paper_id}`;
  const pageLabel =
    source.page_start === source.page_end
      ? `p.${source.page_start}`
      : `pp.${source.page_start}-${source.page_end}`;

  return (
    <article
      id={`source-${source.source_id}`}
      className={[
        "rounded-lg border bg-white p-4 shadow-sm transition",
        active ? "border-[var(--focus-border)] ring-2 ring-[var(--focus-ring)]" : "border-slate-200 hover:border-slate-300",
      ].join(" ")}
    >
      <button type="button" onClick={() => onSourceSelect(source.source_id)} className="block w-full text-left">
        <div className="flex items-start justify-between gap-3">
          <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600">
            {source.source_id}
          </span>
          <span className="rounded-md bg-[var(--brand-blue-soft)] px-2 py-1 text-xs font-semibold text-[var(--brand-ink-soft)]">
            {getRelevanceLabel(index)}
          </span>
        </div>

        <p className="mt-3 text-sm font-semibold leading-5 text-slate-900">{paperLabel}</p>
        <p className="mt-1 text-xs font-medium text-slate-500">
          {pageLabel}
          {source.section_heading ? ` • ${source.section_heading}` : ""}
        </p>
        <p className="mt-3 text-sm leading-6 text-slate-700">{source.excerpt}</p>
      </button>
    </article>
  );
}

export function SourcesPanel({
  open,
  sources,
  activeSourceId,
  onClose,
  onOpen,
  onSourceSelect,
}: SourcesPanelProps) {
  const listRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open || !activeSourceId) {
      return;
    }

    const element = document.getElementById(`source-${activeSourceId}`);
    const container = listRef.current;
    if (!element || !container) {
      return;
    }

    const containerRect = container.getBoundingClientRect();
    const elementRect = element.getBoundingClientRect();
    const offsetTop = elementRect.top - containerRect.top + container.scrollTop;
    container.scrollTo({
      top: Math.max(offsetTop - 16, 0),
      behavior: "smooth",
    });
  }, [activeSourceId, open]);

  if (!open) {
    return (
      <aside className="flex h-full w-16 shrink-0 items-start justify-center border-l border-[var(--border-soft)] bg-[var(--surface-rail)] px-2 pt-4">
        <button
          type="button"
          onClick={onOpen}
          className="flex w-full flex-col items-center gap-2 rounded-xl px-2 py-3 text-slate-500 transition hover:bg-white/70 hover:text-slate-700"
          aria-label="Expand sources panel"
        >
          <span className="relative flex h-10 w-10 items-center justify-center rounded-xl border border-[var(--border-soft)] bg-white text-[var(--brand-ink)] shadow-sm">
            <QuoteIcon />
            {sources.length > 0 ? (
              <span className="absolute -right-1 -top-1 flex h-5 min-w-[20px] items-center justify-center rounded-full bg-[var(--brand-teal)] px-1 text-[10px] font-semibold text-white">
                {sources.length}
              </span>
            ) : null}
          </span>
          <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-400">
            Sources
          </span>
        </button>
      </aside>
    );
  }

  return (
    <aside className="flex h-full w-[344px] shrink-0 flex-col border-l border-[var(--border-soft)] bg-[var(--surface-rail)]">
      <div className="border-b border-slate-200 px-5 py-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-950">Sources</h2>
            <p className="mt-1 text-sm text-slate-500">
              {sources.length > 0 ? "Evidence cited in the current answer" : "No citation selected"}
            </p>
            {sources.length > 0 ? (
              <p className="mt-1 text-xs text-slate-400">Click a source to focus its paper.</p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-slate-500 transition hover:bg-slate-200 hover:text-slate-900"
            aria-label="Collapse sources panel"
          >
            <ChevronIcon collapsed={false} />
          </button>
        </div>
      </div>

      <div ref={listRef} className="flex-1 space-y-4 overflow-y-auto p-4">
        {sources.length > 0 ? (
          sources.map((source, index) => (
            <SourceCard
              key={source.source_id}
              source={source}
              index={index}
              active={source.source_id === activeSourceId}
              onSourceSelect={onSourceSelect}
            />
          ))
        ) : (
          <p className="rounded-lg border border-slate-200 bg-white px-4 py-5 text-sm leading-6 text-slate-500 shadow-sm">
            Click a citation in an assistant answer to inspect the matching evidence here.
          </p>
        )}
      </div>
    </aside>
  );
}
