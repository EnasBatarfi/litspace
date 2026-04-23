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

function TrashIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" aria-hidden="true">
      <path
        d="M4.75 5.5v6m3.25-6v6m3.25-6v6M3.5 4h9M6.25 4V3h3.5v1m-5.5 0 .4 7.05A1 1 0 0 0 5.64 12h4.72a1 1 0 0 0 .99-.95L11.75 4"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.25"
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
  onDeleteProject: (projectId: number) => void;
  onDeleteChat: (projectId: number, chatId: number) => void;
};

function ProjectChats({
  chats,
  projectId,
  activeChatId,
  onChatSelect,
  onNewChat,
  onDeleteChat,
}: {
  chats: ChatSummary[];
  projectId: number;
  activeChatId: number | null;
  onChatSelect: (chatId: number) => void;
  onNewChat: (projectId: number) => void;
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

            return (
              <div
                key={chat.id}
                className={[
                  "group flex items-center gap-2 rounded-md pr-1 transition",
                  active ? "bg-white/8" : "hover:bg-white/5",
                ].join(" ")}
              >
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
                <div className="flex items-center gap-1">
                  {chat.message_count > 0 ? (
                    <span className="rounded-full bg-white/8 px-2 py-0.5 text-[11px] font-medium text-slate-500">
                      {chat.message_count}
                    </span>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => onDeleteChat(projectId, chat.id)}
                    aria-label={`Delete chat ${chat.title}`}
                    className="flex h-7 w-7 items-center justify-center rounded-md text-slate-500 opacity-0 transition hover:bg-white/7 hover:text-rose-200 group-hover:opacity-100"
                  >
                    <TrashIcon />
                  </button>
                </div>
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
  onProjectSelect,
  onProjectToggle,
  onChatSelect,
  onNewChat,
  onDeleteProject,
  onDeleteChat,
}: {
  project: Project;
  active: boolean;
  expanded: boolean;
  chats: ChatSummary[];
  activeChatId: number | null;
  onProjectSelect: (projectId: number) => void;
  onProjectToggle: (projectId: number) => void;
  onChatSelect: (chatId: number) => void;
  onNewChat: (projectId: number) => void;
  onDeleteProject: (projectId: number) => void;
  onDeleteChat: (projectId: number, chatId: number) => void;
}) {
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

        <button
          type="button"
          onClick={() => onDeleteProject(project.id)}
          aria-label={`Delete project ${project.name}`}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-slate-500 opacity-0 transition hover:bg-white/7 hover:text-rose-200 group-hover:opacity-100"
        >
          <TrashIcon />
        </button>
      </div>

      {expanded ? (
        <ProjectChats
          chats={chats}
          projectId={project.id}
          activeChatId={activeChatId}
          onChatSelect={onChatSelect}
          onNewChat={onNewChat}
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
  onDeleteProject,
  onDeleteChat,
}: AppSidebarProps) {
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
                onProjectSelect={onProjectSelect}
                onProjectToggle={onProjectToggle}
                onChatSelect={onChatSelect}
                onNewChat={onNewChat}
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
