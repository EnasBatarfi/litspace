"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import type { ChatSummary, Project } from "@/lib/api";

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      viewBox="0 0 16 16"
      className={["h-4 w-4 transition", open ? "rotate-90" : ""].join(" ")}
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

function PlusIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" aria-hidden="true">
      <path
        d="M8 3.25v9.5M3.25 8h9.5"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.5"
      />
    </svg>
  );
}

function RenameIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" aria-hidden="true">
      <path
        d="m10.75 2.75 2.5 2.5M2.75 13.25l2.8-.55 7-7a1.25 1.25 0 0 0 0-1.75l-.5-.5a1.25 1.25 0 0 0-1.75 0l-7 7-.55 2.8Z"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.2"
      />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" aria-hidden="true">
      <path
        d="m4 4 8 8M12 4l-8 8"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.35"
      />
    </svg>
  );
}

function BrandMark() {
  return (
    <span className="flex h-14 w-14 shrink-0 items-center justify-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-[14px] bg-[linear-gradient(135deg,#4fc2ab,#2f8a76)] shadow-[0_12px_28px_rgba(47,138,118,0.26)]">
        <svg viewBox="0 0 24 24" className="h-[34px] w-[34px]" fill="none" aria-hidden="true">
          <rect x="11.9" y="4.15" width="7.9" height="12.9" rx="2.25" fill="rgba(229,242,238,0.46)" />
          <path
            d="M5.15 3.65h8.05l2.75 2.8V17.4a2.45 2.45 0 0 1-2.45 2.45H5.15A2.45 2.45 0 0 1 2.7 17.4V6.1a2.45 2.45 0 0 1 2.45-2.45Z"
            fill="white"
          />
          <path
            d="M13.2 3.65v3h2.75"
            stroke="var(--brand-teal)"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="1.45"
          />
          <path
            d="M6.8 9.2h6.45M6.8 12.15h6.45M6.8 15.1h4.65"
            stroke="var(--brand-teal)"
            strokeLinecap="round"
            strokeWidth="1.45"
          />
        </svg>
      </span>
    </span>
  );
}

type AppSidebarProps = {
  projects: Project[];
  activeProjectId: number | null;
  activeChatId: number | null;
  chatsByProjectId: Record<number, ChatSummary[]>;
  expandedProjectIds: Record<number, boolean>;
  onOpenCreateProject: () => void;
  onProjectSelect: (projectId: number) => void;
  onProjectToggle: (projectId: number) => void;
  onChatSelect: (chatId: number) => void;
  onNewChat: (projectId: number) => void;
  onRenameProject: (projectId: number, name: string) => Promise<void>;
  onRenameChat: (chatId: number, title: string) => Promise<void>;
  onDeleteProject: (projectId: number) => void;
  onDeleteChat: (projectId: number, chatId: number) => void;
};

type EditingState =
  | {
      kind: "project";
      itemId: number;
      projectId: number;
      value: string;
      originalValue: string;
    }
  | {
      kind: "chat";
      itemId: number;
      projectId: number;
      value: string;
      originalValue: string;
    };

function itemKey(kind: "project" | "chat", itemId: number) {
  return `${kind}-${itemId}`;
}

function IconButton({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className="flex h-7 w-7 items-center justify-center rounded-md text-slate-500 opacity-0 transition hover:bg-white/7 hover:text-slate-100 group-hover:opacity-100"
    >
      {children}
    </button>
  );
}

function TitleEditor({
  value,
  disabled,
  onChange,
  onSubmit,
  onCancel,
}: {
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const cancelOnBlurRef = useRef(false);

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  return (
    <input
      ref={inputRef}
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
      onBlur={() => {
        if (cancelOnBlurRef.current) {
          cancelOnBlurRef.current = false;
          return;
        }
        if (!disabled) {
          onSubmit();
        }
      }}
      onKeyDown={(event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          onSubmit();
        }
        if (event.key === "Escape") {
          event.preventDefault();
          cancelOnBlurRef.current = true;
          onCancel();
        }
      }}
      className="w-full rounded-md border border-white/12 bg-white/8 px-2.5 py-1.5 text-sm font-medium text-white outline-none ring-0 placeholder:text-slate-500 focus:border-[var(--brand-teal)]"
    />
  );
}

function ProjectChats({
  chats,
  projectId,
  activeChatId,
  editing,
  renameLoadingKey,
  renameError,
  onChatSelect,
  onNewChat,
  onStartRename,
  onEditChange,
  onCommitRename,
  onCancelRename,
  onDeleteChat,
}: {
  chats: ChatSummary[];
  projectId: number;
  activeChatId: number | null;
  editing: EditingState | null;
  renameLoadingKey: string | null;
  renameError: string | null;
  onChatSelect: (chatId: number) => void;
  onNewChat: (projectId: number) => void;
  onStartRename: (projectId: number, chat: ChatSummary) => void;
  onEditChange: (value: string) => void;
  onCommitRename: () => void;
  onCancelRename: () => void;
  onDeleteChat: (projectId: number, chatId: number) => void;
}) {
  return (
    <div className="ml-4 mt-2 border-l border-white/8 pl-4">
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
          Chats
        </span>
        <button
          type="button"
          onClick={() => onNewChat(projectId)}
          className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-white/8 bg-white/4 text-slate-300 transition hover:bg-white/8 hover:text-white"
          aria-label="Create new chat"
        >
          <PlusIcon />
        </button>
      </div>

      <div className="space-y-1">
        {chats.length > 0 ? (
          chats.map((chat) => {
            const active = chat.id === activeChatId;
            const editingThisChat =
              editing?.kind === "chat" && editing.itemId === chat.id && editing.projectId === projectId;
            const loadingThisChat = renameLoadingKey === itemKey("chat", chat.id);

            return (
              <div key={chat.id} className="space-y-1">
                <div
                  className={[
                    "group flex items-center gap-2 rounded-md pr-1 transition",
                    active ? "bg-white/8" : "hover:bg-white/5",
                  ].join(" ")}
                >
                  {editingThisChat ? (
                    <div className="min-w-0 flex-1 px-3 py-2">
                      <TitleEditor
                        value={editing.value}
                        disabled={loadingThisChat}
                        onChange={onEditChange}
                        onSubmit={onCommitRename}
                        onCancel={onCancelRename}
                      />
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => onChatSelect(chat.id)}
                      className={[
                        "min-w-0 flex-1 px-3 py-2 text-left text-sm transition",
                        active ? "text-white" : "text-slate-400 group-hover:text-slate-200",
                      ].join(" ")}
                    >
                      <span className="block truncate font-medium">{chat.title}</span>
                    </button>
                  )}

                  <div className="flex items-center gap-1">
                    {!editingThisChat && chat.message_count > 0 ? (
                      <span className="rounded-full bg-white/8 px-2 py-0.5 text-[11px] font-medium text-slate-500">
                        {chat.message_count}
                      </span>
                    ) : null}
                    <IconButton
                      label={`Rename chat ${chat.title}`}
                      onClick={() => onStartRename(projectId, chat)}
                    >
                      <RenameIcon />
                    </IconButton>
                    <button
                      type="button"
                      onClick={() => onDeleteChat(projectId, chat.id)}
                      aria-label={`Delete chat ${chat.title}`}
                      className="flex h-7 w-7 items-center justify-center rounded-md text-slate-500 opacity-0 transition hover:bg-white/7 hover:text-rose-200 group-hover:opacity-100"
                    >
                      <CloseIcon />
                    </button>
                  </div>
                </div>
                {editingThisChat && renameError ? (
                  <p className="px-3 text-[11px] text-rose-300">{renameError}</p>
                ) : null}
              </div>
            );
          })
        ) : (
          <p className="rounded-md border border-white/6 bg-white/4 px-3 py-3 text-sm leading-5 text-slate-500">
            No chats yet.
          </p>
        )}
      </div>
    </div>
  );
}

function ProjectRow({
  project,
  active,
  expanded,
  chats,
  activeChatId,
  editing,
  renameLoadingKey,
  renameError,
  onProjectSelect,
  onProjectToggle,
  onChatSelect,
  onNewChat,
  onStartProjectRename,
  onStartChatRename,
  onEditChange,
  onCommitRename,
  onCancelRename,
  onDeleteProject,
  onDeleteChat,
}: {
  project: Project;
  active: boolean;
  expanded: boolean;
  chats: ChatSummary[];
  activeChatId: number | null;
  editing: EditingState | null;
  renameLoadingKey: string | null;
  renameError: string | null;
  onProjectSelect: (projectId: number) => void;
  onProjectToggle: (projectId: number) => void;
  onChatSelect: (chatId: number) => void;
  onNewChat: (projectId: number) => void;
  onStartProjectRename: (project: Project) => void;
  onStartChatRename: (projectId: number, chat: ChatSummary) => void;
  onEditChange: (value: string) => void;
  onCommitRename: () => void;
  onCancelRename: () => void;
  onDeleteProject: (projectId: number) => void;
  onDeleteChat: (projectId: number, chatId: number) => void;
}) {
  const editingThisProject =
    editing?.kind === "project" && editing.itemId === project.id && editing.projectId === project.id;
  const loadingThisProject = renameLoadingKey === itemKey("project", project.id);

  return (
    <div className="space-y-1.5">
      <div
        className={[
          "group relative flex items-center gap-1 rounded-lg border px-2 py-1.5 transition",
          active
            ? "border-white/10 bg-white/8 shadow-[inset_2px_0_0_var(--brand-teal)]"
            : "border-transparent hover:border-white/6 hover:bg-white/5",
        ].join(" ")}
      >
        <button
          type="button"
          onClick={() => onProjectToggle(project.id)}
          aria-label={expanded ? `Collapse ${project.name}` : `Expand ${project.name}`}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-slate-500 transition hover:bg-white/7 hover:text-white"
        >
          <ChevronIcon open={expanded} />
        </button>

        {editingThisProject ? (
          <div className="min-w-0 flex-1 px-1 py-1.5">
            <TitleEditor
              value={editing.value}
              disabled={loadingThisProject}
              onChange={onEditChange}
              onSubmit={onCommitRename}
              onCancel={onCancelRename}
            />
            <span className="mt-1 block truncate text-xs text-slate-500">
              {project.topic_label || "Project"}
            </span>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => onProjectSelect(project.id)}
            className="min-w-0 flex-1 px-1 py-1.5 text-left"
          >
            <span
              className={[
                "block truncate text-sm font-semibold",
                active ? "text-white" : "text-slate-200 group-hover:text-white",
              ].join(" ")}
            >
              {project.name}
            </span>
            <span className="mt-1 block truncate text-xs text-slate-500">
              {project.topic_label || "Project"}
            </span>
          </button>
        )}

        <div className="flex items-center gap-1">
          <IconButton
            label={`Rename project ${project.name}`}
            onClick={() => onStartProjectRename(project)}
          >
            <RenameIcon />
          </IconButton>
          <button
            type="button"
            onClick={() => onDeleteProject(project.id)}
            aria-label={`Delete project ${project.name}`}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-slate-500 opacity-0 transition hover:bg-white/7 hover:text-rose-200 group-hover:opacity-100"
          >
            <CloseIcon />
          </button>
        </div>
      </div>

      {editingThisProject && renameError ? (
        <p className="px-3 text-[11px] text-rose-300">{renameError}</p>
      ) : null}

      {expanded ? (
        <ProjectChats
          chats={chats}
          projectId={project.id}
          activeChatId={activeChatId}
          editing={editing}
          renameLoadingKey={renameLoadingKey}
          renameError={renameError}
          onChatSelect={onChatSelect}
          onNewChat={onNewChat}
          onStartRename={onStartChatRename}
          onEditChange={onEditChange}
          onCommitRename={onCommitRename}
          onCancelRename={onCancelRename}
          onDeleteChat={onDeleteChat}
        />
      ) : null}
    </div>
  );
}

export function AppSidebar({
  projects,
  activeProjectId,
  activeChatId,
  chatsByProjectId,
  expandedProjectIds,
  onOpenCreateProject,
  onProjectSelect,
  onProjectToggle,
  onChatSelect,
  onNewChat,
  onRenameProject,
  onRenameChat,
  onDeleteProject,
  onDeleteChat,
}: AppSidebarProps) {
  const [editing, setEditing] = useState<EditingState | null>(null);
  const [renameLoadingKey, setRenameLoadingKey] = useState<string | null>(null);
  const [renameError, setRenameError] = useState<string | null>(null);

  function startProjectRename(project: Project) {
    setRenameError(null);
    setEditing({
      kind: "project",
      itemId: project.id,
      projectId: project.id,
      value: project.name,
      originalValue: project.name,
    });
  }

  function startChatRename(projectId: number, chat: ChatSummary) {
    setRenameError(null);
    setEditing({
      kind: "chat",
      itemId: chat.id,
      projectId,
      value: chat.title,
      originalValue: chat.title,
    });
  }

  function cancelRename() {
    setRenameError(null);
    setEditing(null);
  }

  function updateEditingValue(value: string) {
    setRenameError(null);
    setEditing((current) => (current ? { ...current, value } : current));
  }

  async function commitRename() {
    if (!editing) {
      return;
    }

    const nextValue = editing.value.trim();
    if (!nextValue) {
      setRenameError("Name cannot be empty.");
      return;
    }

    if (nextValue === editing.originalValue.trim()) {
      cancelRename();
      return;
    }

    const key = itemKey(editing.kind, editing.itemId);
    try {
      setRenameLoadingKey(key);
      setRenameError(null);

      if (editing.kind === "project") {
        await onRenameProject(editing.itemId, nextValue);
      } else {
        await onRenameChat(editing.itemId, nextValue);
      }

      setEditing(null);
    } catch (error) {
      setRenameError(error instanceof Error ? error.message : "Rename failed");
    } finally {
      setRenameLoadingKey((current) => (current === key ? null : current));
    }
  }

  return (
    <aside className="flex h-screen w-[292px] shrink-0 flex-col overflow-hidden bg-[var(--brand-ink)] text-slate-100">
      <div className="border-b border-white/6 px-5 py-5">
        <div className="flex items-center gap-3">
          <BrandMark />
          <div className="min-w-0">
            <p className="truncate text-[19px] font-semibold tracking-[-0.015em] text-white">
              LitSpace
            </p>
            <p className="text-xs text-slate-400">Project research workspace</p>
          </div>
        </div>
      </div>

      <div className="px-4 py-4">
        <button
          type="button"
          onClick={onOpenCreateProject}
          className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-[var(--brand-teal)] px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[var(--brand-teal-hover)]"
        >
          <PlusIcon />
          <span>New Project</span>
        </button>
      </div>

      <div className="flex items-center justify-between px-5 pb-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
          Projects
        </span>
        <span className="rounded-full bg-white/6 px-2 py-0.5 text-[11px] font-medium text-slate-400">
          {projects.length}
        </span>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-5">
        {projects.length > 0 ? (
          <div className="space-y-2">
            {projects.map((project) => (
              <ProjectRow
                key={project.id}
                project={project}
                active={project.id === activeProjectId}
                expanded={Boolean(expandedProjectIds[project.id])}
                chats={chatsByProjectId[project.id] || []}
                activeChatId={activeChatId}
                editing={editing}
                renameLoadingKey={renameLoadingKey}
                renameError={renameError}
                onProjectSelect={onProjectSelect}
                onProjectToggle={onProjectToggle}
                onChatSelect={onChatSelect}
                onNewChat={onNewChat}
                onStartProjectRename={startProjectRename}
                onStartChatRename={startChatRename}
                onEditChange={updateEditingValue}
                onCommitRename={() => void commitRename()}
                onCancelRename={cancelRename}
                onDeleteProject={onDeleteProject}
                onDeleteChat={onDeleteChat}
              />
            ))}
          </div>
        ) : (
          <div className="rounded-lg border border-white/6 bg-white/4 px-4 py-5 text-sm leading-6 text-slate-400">
            No projects yet.
          </div>
        )}
      </div>
    </aside>
  );
}
