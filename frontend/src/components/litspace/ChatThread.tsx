"use client";

import { useEffect, useRef } from "react";
import type { ChatMessage } from "@/lib/api";
import { ChatInputBar } from "./ChatInputBar";
import { QuickActionsBar } from "./QuickActionsBar";
import type { SelectedCitation } from "./types";

const CITATION_GROUP_RE = /\[(?:S\d+(?:,\s*S\d+)*)\]/g;
const CITATION_TOKEN_RE = /^\[((?:S\d+(?:,\s*S\d+)*))\]$/;

type AnswerSegment =
  | {
      type: "text";
      content: string;
    }
  | {
      type: "citations";
      sourceIds: string[];
    };

type ChatThreadProps = {
  projectName: string | null;
  hasProject: boolean;
  hasChat: boolean;
  paperCount: number;
  messages: ChatMessage[];
  selectedCitation: SelectedCitation;
  draft: string;
  loading: boolean;
  error: string | null;
  disabled: boolean;
  onDraftChange: (value: string) => void;
  onSubmit: () => void;
  onCitationClick: (messageId: number, sourceId: string) => void;
  onQuickAction: (action: string) => void;
  onOpenCreateProject: () => void;
  onNewChat: () => void;
};

function ActionButton({
  label,
  onClick,
  primary = false,
}: {
  label: string;
  onClick: () => void;
  primary?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "rounded-md px-4 py-2.5 text-sm font-semibold transition",
        primary
          ? "bg-[var(--brand-teal)] text-white shadow-sm hover:bg-[var(--brand-teal-hover)]"
          : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50",
      ].join(" ")}
    >
      {label}
    </button>
  );
}

function CitationButton({
  sourceId,
  active,
  onClick,
}: {
  sourceId: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "inline-flex rounded-md px-1.5 py-0.5 text-xs font-semibold transition",
        active ? "bg-[var(--brand-teal)] text-white" : "bg-[var(--brand-blue-soft)] text-[var(--brand-ink-soft)] hover:bg-[var(--focus-ring)]",
      ].join(" ")}
      aria-label={`Open source ${sourceId}`}
    >
      [{sourceId}]
    </button>
  );
}

function parseAnswerSegments(content: string): AnswerSegment[] {
  const parts = content.split(new RegExp(`(${CITATION_GROUP_RE.source})`, "g"));
  const segments: AnswerSegment[] = [];

  for (let index = 0; index < parts.length; index += 1) {
    const part = parts[index];
    if (!part) {
      continue;
    }

    const citationMatch = part.match(CITATION_TOKEN_RE);
    if (citationMatch) {
      const sourceIds = citationMatch[1].split(/\s*,\s*/);
      const previousSegment = segments[segments.length - 1];
      if (previousSegment?.type === "citations") {
        previousSegment.sourceIds.push(...sourceIds);
      } else {
        segments.push({ type: "citations", sourceIds });
      }
      continue;
    }

    const previousIsCitation = CITATION_TOKEN_RE.test(parts[index - 1] || "");
    const nextIsCitation = CITATION_TOKEN_RE.test(parts[index + 1] || "");
    if (part.trim() === "" && previousIsCitation && nextIsCitation) {
      continue;
    }

    const previousSegment = segments[segments.length - 1];
    if (previousSegment?.type === "text") {
      previousSegment.content += part;
    } else {
      segments.push({ type: "text", content: part });
    }
  }

  return segments;
}

function renderAnswerWithCitations({
  message,
  selectedCitation,
  onCitationClick,
}: {
  message: ChatMessage;
  selectedCitation: SelectedCitation;
  onCitationClick: (messageId: number, sourceId: string) => void;
}) {
  const segments = parseAnswerSegments(message.content);

  return segments.map((segment, index) => {
    if (segment.type === "text") {
      return (
        <span key={`${message.id}-text-${index}-${segment.content.slice(0, 12)}`}>
          {segment.content}
        </span>
      );
    }

    return (
      <span key={`${message.id}-group-${index}`} className="inline-flex flex-wrap items-center gap-1 align-middle">
        {segment.sourceIds.map((sourceId) => (
          <CitationButton
            key={`${message.id}-${sourceId}-${index}`}
            sourceId={sourceId}
            active={selectedCitation?.messageId === message.id && selectedCitation?.sourceId === sourceId}
            onClick={() => onCitationClick(message.id, sourceId)}
          />
        ))}
      </span>
    );
  });
}

function NoProjectState({ onOpenCreateProject }: { onOpenCreateProject: () => void }) {
  return (
    <div className="mx-auto flex max-w-[760px] flex-1 items-center justify-center px-6 py-10">
      <div className="w-full rounded-2xl border border-slate-200 bg-white px-8 py-10 text-center shadow-[0_24px_80px_rgba(15,23,42,0.08)]">
        <p className="text-sm font-semibold uppercase tracking-[0.08em] text-[var(--brand-teal)]">
          Project workspace
        </p>
        <h2 className="mt-3 text-3xl font-semibold text-slate-950">Create your first project</h2>
        <p className="mx-auto mt-3 max-w-[560px] text-sm leading-6 text-slate-500">
          Projects hold the papers, chats, and grounded answers that belong together.
        </p>
        <div className="mt-6 flex justify-center">
          <ActionButton label="Create Project" onClick={onOpenCreateProject} primary />
        </div>
      </div>
    </div>
  );
}

function NoChatState({
  projectName,
  paperCount,
  onNewChat,
}: {
  projectName: string;
  paperCount: number;
  onNewChat: () => void;
}) {
  return (
    <div className="mx-auto flex max-w-[760px] flex-1 items-center justify-center px-6 py-10">
      <div className="w-full rounded-2xl border border-slate-200 bg-white px-8 py-10 shadow-[0_24px_80px_rgba(15,23,42,0.08)]">
        <p className="text-sm font-semibold uppercase tracking-[0.08em] text-[var(--brand-teal)]">{projectName}</p>
        <h2 className="mt-3 text-3xl font-semibold text-slate-950">Start a new chat</h2>
        <p className="mt-3 max-w-[600px] text-sm leading-6 text-slate-500">
          Chats stay inside the project. The {paperCount} project papers remain shared across every
          thread you create here.
        </p>
        <div className="mt-6">
          <ActionButton label="+ New Chat" onClick={onNewChat} primary />
        </div>
      </div>
    </div>
  );
}

function EmptyThread({
  projectName,
  paperCount,
}: {
  projectName: string;
  paperCount: number;
}) {
  return (
    <div className="mx-auto mt-10 max-w-[760px] rounded-2xl border border-dashed border-slate-300 bg-white px-8 py-10 text-center shadow-sm">
      <p className="text-sm font-semibold uppercase tracking-[0.08em] text-[var(--brand-teal)]">Grounded chat</p>
      <h2 className="mt-3 text-2xl font-semibold text-slate-950">Ask a question about {projectName}</h2>
      <p className="mx-auto mt-3 max-w-[560px] text-sm leading-6 text-slate-500">
        Answers stay in this conversation. Citations open the sources panel, and the {paperCount}{" "}
        project papers remain shared across every chat.
      </p>
    </div>
  );
}

function UserMessage({ message }: { message: ChatMessage }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[72%] rounded-2xl rounded-br-md bg-[var(--brand-blue-soft)] px-5 py-4 text-[15px] leading-7 text-slate-900 shadow-[0_10px_24px_rgba(15,23,42,0.05)]">
        {message.content}
      </div>
    </div>
  );
}

function AssistantMessage({
  message,
  selectedCitation,
  onCitationClick,
}: {
  message: ChatMessage;
  selectedCitation: SelectedCitation;
  onCitationClick: (messageId: number, sourceId: string) => void;
}) {
  return (
    <article className="max-w-[860px] rounded-2xl rounded-tl-md border border-slate-200/90 bg-white px-6 py-5 shadow-[0_16px_44px_rgba(15,23,42,0.06)]">
      <div className="mb-3 flex items-center gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--brand-teal-soft)] text-sm font-semibold text-[var(--brand-ink)]">
          L
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-950">LitSpace</p>
          <p className="text-xs text-slate-500">
            {message.sources.length > 0 ? `${message.sources.length} cited sources` : "Answer"}
          </p>
        </div>
      </div>

      <div className="whitespace-pre-wrap text-[15px] leading-7 text-slate-900">
        {renderAnswerWithCitations({ message, selectedCitation, onCitationClick })}
      </div>

      {message.insufficient_evidence ? (
        <p className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm leading-5 text-amber-800">
          The backend marked this answer as having limited supporting evidence.
        </p>
      ) : null}
    </article>
  );
}

function LoadingMessage() {
  return (
    <div className="max-w-[860px] rounded-2xl rounded-tl-md border border-slate-200 bg-white px-6 py-5 text-sm font-medium text-slate-500 shadow-sm">
      Retrieving evidence and generating a grounded answer...
    </div>
  );
}

export function ChatThread({
  projectName,
  hasProject,
  hasChat,
  paperCount,
  messages,
  selectedCitation,
  draft,
  loading,
  error,
  disabled,
  onDraftChange,
  onSubmit,
  onCitationClick,
  onQuickAction,
  onOpenCreateProject,
  onNewChat,
}: ChatThreadProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length, loading]);

  return (
    <main className="flex min-w-[520px] flex-1 flex-col bg-[var(--surface-muted)]">
      {!hasProject ? (
        <NoProjectState onOpenCreateProject={onOpenCreateProject} />
      ) : !hasChat ? (
        <NoChatState projectName={projectName || "this project"} paperCount={paperCount} onNewChat={onNewChat} />
      ) : (
        <>
          <div className="flex-1 overflow-y-auto px-6 py-7">
            {messages.length === 0 && !loading ? (
              <EmptyThread projectName={projectName || "this project"} paperCount={paperCount} />
            ) : (
              <div className="mx-auto flex max-w-[920px] flex-col gap-6">
                {messages.map((message) =>
                  message.role === "user" ? (
                    <UserMessage key={message.id} message={message} />
                  ) : (
                    <AssistantMessage
                      key={message.id}
                      message={message}
                      selectedCitation={selectedCitation}
                      onCitationClick={onCitationClick}
                    />
                  ),
                )}
                {loading ? <LoadingMessage /> : null}
                {error ? (
                  <div className="rounded-lg border border-rose-200 bg-rose-50 px-5 py-4 text-sm text-rose-700">
                    {error}
                  </div>
                ) : null}
                <div ref={bottomRef} />
              </div>
            )}
          </div>

          <div className="border-t border-slate-200 bg-white/95 px-4 py-4 backdrop-blur">
            <div className="mx-auto max-w-[920px] rounded-2xl border border-slate-200 bg-white shadow-[0_20px_48px_rgba(15,23,42,0.06)]">
              <QuickActionsBar disabled={disabled} onActionSelect={onQuickAction} />
              <ChatInputBar value={draft} disabled={disabled || loading} onChange={onDraftChange} onSubmit={onSubmit} />
            </div>
          </div>
        </>
      )}
    </main>
  );
}
