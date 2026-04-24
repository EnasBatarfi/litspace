"use client";

import { Fragment, useEffect, useRef, useState } from "react";
import type { ChatMessage, Paper } from "@/lib/api";
import { ChatInputBar } from "./ChatInputBar";
import { QuickActionsBar } from "./QuickActionsBar";
import type { SelectedCitation } from "./types";

const INLINE_TOKEN_RE = /(\*\*([^*]+)\*\*|\[((?:S\d+(?:\s*,\s*S\d+)*))\])/g;
const UNORDERED_LIST_RE = /^\s*[-*]\s+(.*)$/;
const ORDERED_LIST_RE = /^\s*\d+\.\s+(.*)$/;
const BLOCKQUOTE_RE = /^\s*>\s?(.*)$/;
const HEADING_RE = /^(#{1,6})\s+(.*)$/;
const TABLE_SEPARATOR_RE = /^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$/;

type InlineNode =
  | {
      type: "text";
      content: string;
    }
  | {
      type: "bold";
      children: InlineNode[];
    }
  | {
      type: "citations";
      sourceIds: string[];
    };

type AnswerBlock =
  | {
      type: "heading";
      level: number;
      content: string;
    }
  | {
      type: "paragraph";
      lines: string[];
    }
  | {
      type: "unordered-list";
      items: string[];
    }
  | {
      type: "ordered-list";
      items: string[];
    }
  | {
      type: "blockquote";
      lines: string[];
    }
  | {
      type: "table";
      headers: string[];
      rows: string[][];
    };

type ChatThreadProps = {
  projectName: string | null;
  hasProject: boolean;
  hasChat: boolean;
  paperCount: number;
  messages: ChatMessage[];
  selectedPapers: Paper[];
  selectedCitation: SelectedCitation;
  draft: string;
  loading: boolean;
  error: string | null;
  validationMessage: string | null;
  disabled: boolean;
  onDraftChange: (value: string) => void;
  onSubmit: () => void;
  onCitationClick: (messageId: number, sourceId: string) => void;
  onQuickAction: (action: string) => void;
  onRemoveSelectedPaper: (paperId: number) => void;
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

function CopyIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" aria-hidden="true">
      <path
        d="M5.5 5.5h5.25A1.25 1.25 0 0 1 12 6.75V12a1.25 1.25 0 0 1-1.25 1.25H5.5A1.25 1.25 0 0 1 4.25 12V6.75A1.25 1.25 0 0 1 5.5 5.5Z"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.3"
      />
      <path
        d="M3.75 10.5h-.5A1.25 1.25 0 0 1 2 9.25V4a1.25 1.25 0 0 1 1.25-1.25H8.5A1.25 1.25 0 0 1 9.75 4v.5"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.3"
      />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" aria-hidden="true">
      <path
        d="M3.25 8.25 6.5 11.5l6.25-7"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.45"
      />
    </svg>
  );
}

function CopyButton({
  copied,
  onClick,
}: {
  copied: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={copied ? "Copied" : "Copy message"}
      title={copied ? "Copied" : "Copy message"}
      className="inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
    >
      {copied ? <CheckIcon /> : <CopyIcon />}
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

function parseInlineNodes(content: string, depth = 0): InlineNode[] {
  if (!content) {
    return [];
  }

  const nodes: InlineNode[] = [];
  let cursor = 0;

  for (const match of content.matchAll(INLINE_TOKEN_RE)) {
    const token = match[0];
    const index = match.index ?? 0;

    if (index > cursor) {
      nodes.push({ type: "text", content: content.slice(cursor, index) });
    }

    if (match[2]) {
      nodes.push({
        type: "bold",
        children: depth >= 2 ? [{ type: "text", content: match[2] }] : parseInlineNodes(match[2], depth + 1),
      });
    } else if (match[3]) {
      nodes.push({
        type: "citations",
        sourceIds: match[3].split(/\s*,\s*/),
      });
    } else if (token) {
      nodes.push({ type: "text", content: token });
    }

    cursor = index + token.length;
  }

  if (cursor < content.length) {
    nodes.push({ type: "text", content: content.slice(cursor) });
  }

  return nodes;
}

function parseAnswerBlocks(content: string): AnswerBlock[] {
  const lines = content.replace(/\r/g, "").split("\n");
  const blocks: AnswerBlock[] = [];
  let paragraphLines: string[] = [];

  const splitTableRow = (line: string) =>
    line
      .trim()
      .replace(/^\|/, "")
      .replace(/\|$/, "")
      .split("|")
      .map((cell) => cell.trim());

  const splitTabbedRow = (line: string) =>
    line
      .split("\t")
      .map((cell) => cell.trim())
      .filter((cell) => cell.length > 0);

  const flushParagraph = () => {
    if (paragraphLines.length === 0) {
      return;
    }
    blocks.push({ type: "paragraph", lines: paragraphLines });
    paragraphLines = [];
  };

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const trimmed = line.trim();

    if (!trimmed) {
      flushParagraph();
      continue;
    }

    const headingMatch = trimmed.match(HEADING_RE);
    if (headingMatch) {
      flushParagraph();
      blocks.push({
        type: "heading",
        level: headingMatch[1].length,
        content: headingMatch[2],
      });
      continue;
    }

    if (
      line.includes("|") &&
      index + 1 < lines.length &&
      TABLE_SEPARATOR_RE.test(lines[index + 1])
    ) {
      flushParagraph();
      const headers = splitTableRow(line);
      const rows: string[][] = [];
      let cursor = index + 2;

      while (cursor < lines.length) {
        const rowLine = lines[cursor];
        if (!rowLine.trim() || !rowLine.includes("|")) {
          break;
        }
        rows.push(splitTableRow(rowLine));
        cursor += 1;
      }

      blocks.push({ type: "table", headers, rows });
      index = cursor - 1;
      continue;
    }

    if (line.includes("\t")) {
      const headers = splitTabbedRow(line);
      if (headers.length >= 2) {
        const rows: string[][] = [];
        let cursor = index + 1;

        while (cursor < lines.length) {
          const rowLine = lines[cursor];
          if (!rowLine.trim() || !rowLine.includes("\t")) {
            break;
          }
          const cells = splitTabbedRow(rowLine);
          if (cells.length < 2) {
            break;
          }
          rows.push(cells);
          cursor += 1;
        }

        if (rows.length > 0) {
          flushParagraph();
          blocks.push({ type: "table", headers, rows });
          index = cursor - 1;
          continue;
        }
      }
    }

    const blockquoteMatch = line.match(BLOCKQUOTE_RE);
    if (blockquoteMatch) {
      flushParagraph();
      const quoteLines: string[] = [];
      let cursor = index;
      while (cursor < lines.length) {
        const quoteLine = lines[cursor].match(BLOCKQUOTE_RE);
        if (!quoteLine) {
          break;
        }
        quoteLines.push(quoteLine[1]);
        cursor += 1;
      }
      blocks.push({ type: "blockquote", lines: quoteLines });
      index = cursor - 1;
      continue;
    }

    const unorderedMatch = line.match(UNORDERED_LIST_RE);
    if (unorderedMatch) {
      flushParagraph();
      const items: string[] = [];
      let cursor = index;
      while (cursor < lines.length) {
        const listMatch = lines[cursor].match(UNORDERED_LIST_RE);
        if (!listMatch) {
          break;
        }
        items.push(listMatch[1]);
        cursor += 1;
      }
      blocks.push({ type: "unordered-list", items });
      index = cursor - 1;
      continue;
    }

    const orderedMatch = line.match(ORDERED_LIST_RE);
    if (orderedMatch) {
      flushParagraph();
      const items: string[] = [];
      let cursor = index;
      while (cursor < lines.length) {
        const listMatch = lines[cursor].match(ORDERED_LIST_RE);
        if (!listMatch) {
          break;
        }
        items.push(listMatch[1]);
        cursor += 1;
      }
      blocks.push({ type: "ordered-list", items });
      index = cursor - 1;
      continue;
    }

    paragraphLines.push(trimmed);
  }

  flushParagraph();
  return blocks;
}

function renderInlineNodes({
  nodes,
  message,
  selectedCitation,
  onCitationClick,
}: {
  nodes: InlineNode[];
  message: ChatMessage;
  selectedCitation: SelectedCitation;
  onCitationClick: (messageId: number, sourceId: string) => void;
}) {
  return nodes.map((node, index) => {
    if (node.type === "text") {
      return <Fragment key={`${message.id}-text-${index}`}>{node.content}</Fragment>;
    }

    if (node.type === "bold") {
      return (
        <strong key={`${message.id}-bold-${index}`} className="font-semibold text-slate-950">
          {renderInlineNodes({
            nodes: node.children,
            message,
            selectedCitation,
            onCitationClick,
          })}
        </strong>
      );
    }

    return (
      <span key={`${message.id}-group-${index}`} className="inline-flex flex-wrap items-center gap-1 align-middle">
        {node.sourceIds.map((sourceId) => (
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

function renderStructuredAnswer({
  message,
  selectedCitation,
  onCitationClick,
}: {
  message: ChatMessage;
  selectedCitation: SelectedCitation;
  onCitationClick: (messageId: number, sourceId: string) => void;
}) {
  const blocks = parseAnswerBlocks(message.content);

  const renderLine = (content: string, key: string) =>
    renderInlineNodes({
      nodes: parseInlineNodes(content),
      message,
      selectedCitation,
      onCitationClick,
    }).map((node, index) => <Fragment key={`${key}-${index}`}>{node}</Fragment>);

  return (
    <div className="space-y-4 text-[15px] leading-7 text-slate-900">
      {blocks.map((block, blockIndex) => {
        if (block.type === "heading") {
          const className =
            block.level <= 2
              ? "text-xl font-semibold text-slate-950"
              : block.level === 3
                ? "text-lg font-semibold text-slate-950"
                : "text-base font-semibold text-slate-900";
          return (
            <div key={`${message.id}-heading-${blockIndex}`} className={className}>
              {renderLine(block.content, `${message.id}-heading-${blockIndex}`)}
            </div>
          );
        }

        if (block.type === "paragraph") {
          return (
            <p key={`${message.id}-paragraph-${blockIndex}`}>
              {block.lines.map((line, lineIndex) => (
                <Fragment key={`${message.id}-paragraph-${blockIndex}-${lineIndex}`}>
                  {renderLine(line, `${message.id}-paragraph-${blockIndex}-${lineIndex}`)}
                  {lineIndex < block.lines.length - 1 ? <br /> : null}
                </Fragment>
              ))}
            </p>
          );
        }

        if (block.type === "unordered-list") {
          return (
            <ul key={`${message.id}-ul-${blockIndex}`} className="list-disc space-y-2 pl-5 marker:text-slate-400">
              {block.items.map((item, itemIndex) => (
                <li key={`${message.id}-ul-${blockIndex}-${itemIndex}`}>
                  {renderLine(item, `${message.id}-ul-${blockIndex}-${itemIndex}`)}
                </li>
              ))}
            </ul>
          );
        }

        if (block.type === "ordered-list") {
          return (
            <ol key={`${message.id}-ol-${blockIndex}`} className="list-decimal space-y-2 pl-5 marker:text-slate-400">
              {block.items.map((item, itemIndex) => (
                <li key={`${message.id}-ol-${blockIndex}-${itemIndex}`}>
                  {renderLine(item, `${message.id}-ol-${blockIndex}-${itemIndex}`)}
                </li>
              ))}
            </ol>
          );
        }

        if (block.type === "table") {
          return (
            <div key={`${message.id}-table-${blockIndex}`} className="overflow-x-auto rounded-xl border border-slate-200">
              <table className="min-w-full border-collapse bg-white text-sm leading-6">
                <thead className="bg-slate-50">
                  <tr>
                    {block.headers.map((header, headerIndex) => (
                      <th
                        key={`${message.id}-table-${blockIndex}-header-${headerIndex}`}
                        className="border-b border-slate-200 px-4 py-2 text-left font-semibold text-slate-900"
                      >
                        {renderLine(
                          header,
                          `${message.id}-table-${blockIndex}-header-${headerIndex}`,
                        )}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {block.rows.map((row, rowIndex) => (
                    <tr key={`${message.id}-table-${blockIndex}-row-${rowIndex}`} className="border-t border-slate-100">
                      {row.map((cell, cellIndex) => (
                        <td
                          key={`${message.id}-table-${blockIndex}-cell-${rowIndex}-${cellIndex}`}
                          className="px-4 py-2 align-top text-slate-700"
                        >
                          {renderLine(
                            cell,
                            `${message.id}-table-${blockIndex}-cell-${rowIndex}-${cellIndex}`,
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }

        return (
          <blockquote
            key={`${message.id}-quote-${blockIndex}`}
            className="border-l-2 border-slate-200 pl-4 text-slate-700"
          >
            {block.lines.map((line, lineIndex) => (
              <Fragment key={`${message.id}-quote-${blockIndex}-${lineIndex}`}>
                {renderLine(line, `${message.id}-quote-${blockIndex}-${lineIndex}`)}
                {lineIndex < block.lines.length - 1 ? <br /> : null}
              </Fragment>
            ))}
          </blockquote>
        );
      })}
    </div>
  );
}

function getInputPlaceholder() {
  return "Ask about one paper, selected papers, all papers, or a claim from this project...";
}

function getPaperChipLabel(paper: Paper) {
  return paper.title || paper.original_filename;
}

function RemoveChipIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-3 w-3" fill="none" aria-hidden="true">
      <path
        d="m4.5 4.5 7 7m0-7-7 7"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.35"
      />
    </svg>
  );
}

function SelectedPaperChips({
  papers,
  onRemove,
}: {
  papers: Paper[];
  onRemove: (paperId: number) => void;
}) {
  if (papers.length === 0) {
    return null;
  }

  return (
    <div className="px-5 pt-3">
      <div className="rounded-2xl border border-slate-200 bg-white/90 px-4 py-3 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-400">
            Selected Papers
          </span>
          {papers.map((paper) => (
            <span
              key={paper.id}
              className="inline-flex max-w-full items-center gap-2 rounded-full bg-[var(--brand-blue-soft)] px-3 py-1.5 text-xs font-medium text-[var(--brand-ink-soft)]"
            >
              <span className="truncate">{getPaperChipLabel(paper)}</span>
              <button
                type="button"
                onClick={() => onRemove(paper.id)}
                className="inline-flex h-4 w-4 items-center justify-center rounded-full text-[var(--brand-ink-soft)]/80 transition hover:bg-white/60 hover:text-[var(--brand-ink-soft)]"
                aria-label={`Remove ${getPaperChipLabel(paper)} from selected papers`}
              >
                <RemoveChipIcon />
              </button>
            </span>
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Selected papers define the default scope for the next question unless you name a paper or
          use a visible paper number in the message.
        </p>
      </div>
    </div>
  );
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

function UserMessage({
  message,
  copied,
  onCopy,
}: {
  message: ChatMessage;
  copied: boolean;
  onCopy: () => void;
}) {
  return (
    <div className="flex justify-end">
      <div className="group flex max-w-[72%] flex-col items-end gap-2">
        <div className="rounded-2xl rounded-br-md bg-[var(--brand-blue-soft)] px-5 py-4 text-[15px] leading-7 text-slate-900 shadow-[0_10px_24px_rgba(15,23,42,0.05)]">
          <span className="whitespace-pre-wrap">{message.content}</span>
        </div>
        <CopyButton copied={copied} onClick={onCopy} />
      </div>
    </div>
  );
}

function AssistantMessage({
  message,
  selectedCitation,
  onCitationClick,
  copied,
  onCopy,
}: {
  message: ChatMessage;
  selectedCitation: SelectedCitation;
  onCitationClick: (messageId: number, sourceId: string) => void;
  copied: boolean;
  onCopy: () => void;
}) {
  return (
    <div className="group flex max-w-[860px] flex-col gap-2">
      <article className="rounded-2xl rounded-tl-md border border-slate-200/90 bg-white px-6 py-5 shadow-[0_16px_44px_rgba(15,23,42,0.06)]">
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
        {renderStructuredAnswer({ message, selectedCitation, onCitationClick })}
      </article>
      <CopyButton copied={copied} onClick={onCopy} />
    </div>
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
  selectedPapers,
  selectedCitation,
  draft,
  loading,
  error,
  validationMessage,
  disabled,
  onDraftChange,
  onSubmit,
  onCitationClick,
  onQuickAction,
  onRemoveSelectedPaper,
  onOpenCreateProject,
  onNewChat,
}: ChatThreadProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const [copiedMessageId, setCopiedMessageId] = useState<number | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length, loading]);

  async function copyMessage(message: ChatMessage) {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopiedMessageId(message.id);
      window.setTimeout(() => {
        setCopiedMessageId((current) => (current === message.id ? null : current));
      }, 1600);
    } catch {
      setCopiedMessageId(null);
    }
  }

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
                    <UserMessage
                      key={message.id}
                      message={message}
                      copied={copiedMessageId === message.id}
                      onCopy={() => void copyMessage(message)}
                    />
                  ) : (
                    <AssistantMessage
                      key={message.id}
                      message={message}
                      selectedCitation={selectedCitation}
                      onCitationClick={onCitationClick}
                      copied={copiedMessageId === message.id}
                      onCopy={() => void copyMessage(message)}
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

          <div className="px-4 py-4">
            <div className="mx-auto max-w-[920px]">
              <QuickActionsBar disabled={disabled} onActionSelect={onQuickAction} />
              <SelectedPaperChips papers={selectedPapers} onRemove={onRemoveSelectedPaper} />
              <ChatInputBar
                value={draft}
                placeholder={getInputPlaceholder()}
                disabled={disabled || loading}
                validationMessage={validationMessage}
                onChange={onDraftChange}
                onSubmit={onSubmit}
              />
            </div>
          </div>
        </>
      )}
    </main>
  );
}
