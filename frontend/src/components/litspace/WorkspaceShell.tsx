"use client";

import { useEffect, useMemo, useState } from "react";
import {
  askProject,
  chunkPaper,
  createProject,
  createProjectChat,
  deleteChat as deleteChatRequest,
  deleteProject,
  deleteProjectPaper,
  getChat,
  indexProject,
  listProjectChats,
  listProjectPapers,
  listProjects,
  parsePaper,
  uploadProjectPaper,
  type Chat,
  type ChatMessage,
  type ChatSummary,
  type CreateProjectPayload,
  type Paper,
  type Project,
} from "@/lib/api";
import { AppSidebar } from "./AppSidebar";
import { ChatThread } from "./ChatThread";
import { CreateProjectModal } from "./CreateProjectModal";
import { DeleteItemModal } from "./DeleteItemModal";
import { PapersPanel } from "./PapersPanel";
import { SourcesPanel } from "./SourcesPanel";
import type { SelectedCitation } from "./types";
import { WorkspaceHeader } from "./WorkspaceHeader";

const NEW_CHAT_TITLE = "New chat";
const CITATION_GROUP_RE = /\[(S\d+(?:,\s*S\d+)*)\]/g;

type DeleteTarget =
  | {
      kind: "project";
      projectId: number;
      label: string;
    }
  | {
      kind: "chat";
      projectId: number;
      chatId: number;
      label: string;
    }
  | {
      kind: "paper";
      projectId: number;
      paperId: number;
      label: string;
    };

function titleFromQuestion(question: string) {
  const compact = question.replace(/\s+/g, " ").trim();
  return compact.length > 56 ? `${compact.slice(0, 53)}...` : compact;
}

function extractCitationIds(text: string) {
  const orderedIds: string[] = [];
  const seen = new Set<string>();

  for (const match of text.matchAll(CITATION_GROUP_RE)) {
    const group = match[1];
    for (const sourceId of group.split(/\s*,\s*/)) {
      if (!seen.has(sourceId)) {
        seen.add(sourceId);
        orderedIds.push(sourceId);
      }
    }
  }

  return orderedIds;
}

function sortChats(chats: ChatSummary[]) {
  return [...chats].sort(
    (left, right) =>
      new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime(),
  );
}

function toChatSummary(chat: Chat): ChatSummary {
  return {
    id: chat.id,
    project_id: chat.project_id,
    title: chat.title,
    message_count: chat.messages.length,
    created_at: chat.created_at,
    updated_at: chat.updated_at,
  };
}

export function WorkspaceShell() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<number | null>(null);
  const [activePaperId, setActivePaperId] = useState<number | null>(null);
  const [activeChatId, setActiveChatId] = useState<number | null>(null);
  const [chatsByProjectId, setChatsByProjectId] = useState<Record<number, ChatSummary[]>>({});
  const [chatDetailsById, setChatDetailsById] = useState<Record<number, Chat>>({});
  const [draftByChatId, setDraftByChatId] = useState<Record<number, string>>({});
  const [expandedProjectIds, setExpandedProjectIds] = useState<Record<number, boolean>>({});
  const [papersPanelOpen, setPapersPanelOpen] = useState(true);
  const [sourcePanelOpen, setSourcePanelOpen] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<SelectedCitation>(null);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [papersLoading, setPapersLoading] = useState(false);
  const [chatDetailLoadingId, setChatDetailLoadingId] = useState<number | null>(null);
  const [submittingChatIds, setSubmittingChatIds] = useState<Record<number, boolean>>({});
  const [uploading, setUploading] = useState(false);
  const [projectError, setProjectError] = useState<string | null>(null);
  const [paperError, setPaperError] = useState<string | null>(null);
  const [chatErrors, setChatErrors] = useState<Record<number, string | null>>({});
  const [createProjectOpen, setCreateProjectOpen] = useState(false);
  const [createProjectLoading, setCreateProjectLoading] = useState(false);
  const [createProjectError, setCreateProjectError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const activeProject = useMemo(
    () => projects.find((project) => project.id === activeProjectId) || null,
    [activeProjectId, projects],
  );

  const activeProjectChats = useMemo(
    () => (activeProjectId ? chatsByProjectId[activeProjectId] || [] : []),
    [activeProjectId, chatsByProjectId],
  );

  const activeChatSummary = useMemo(
    () =>
      activeChatId && activeProjectId
        ? activeProjectChats.find((chat) => chat.id === activeChatId) || null
        : null,
    [activeChatId, activeProjectChats, activeProjectId],
  );

  const activeChat = useMemo(() => {
    if (!activeChatId || !activeProjectId) {
      return null;
    }

    const chat = chatDetailsById[activeChatId];
    if (!chat || chat.project_id !== activeProjectId) {
      return null;
    }

    return chat;
  }, [activeChatId, activeProjectId, chatDetailsById]);

  const indexedCount = useMemo(
    () => papers.filter((paper) => paper.status === "indexed").length,
    [papers],
  );

  const selectedSources = useMemo(() => {
    if (!selectedCitation) {
      return [];
    }

    const chat = chatDetailsById[selectedCitation.chatId];
    if (!chat) {
      return [];
    }

    const message = chat.messages.find((item) => item.id === selectedCitation.messageId);
    if (!message || message.role !== "assistant") {
      return [];
    }

    const citedIds = extractCitationIds(message.content);
    const sourceMap = new Map(message.sources.map((source) => [source.source_id, source]));
    const citedSources = citedIds
      .map((sourceId) => sourceMap.get(sourceId))
      .filter((source): source is NonNullable<typeof source> => Boolean(source));

    return citedSources.length > 0 ? citedSources : message.sources;
  }, [chatDetailsById, selectedCitation]);

  const activeDraft = activeChatId ? draftByChatId[activeChatId] || "" : "";
  const activeChatError = activeChatId ? chatErrors[activeChatId] || null : null;
  const answerLoading = activeChatId ? Boolean(submittingChatIds[activeChatId]) : false;
  const chatLoading =
    activeChatId !== null &&
    chatDetailLoadingId === activeChatId &&
    !chatDetailsById[activeChatId];

  function upsertChat(chat: Chat) {
    setChatDetailsById((current) => ({ ...current, [chat.id]: chat }));
    setChatsByProjectId((current) => {
      const summary = toChatSummary(chat);
      const projectChats = current[chat.project_id] || [];
      const nextChats = projectChats.some((item) => item.id === chat.id)
        ? projectChats.map((item) => (item.id === chat.id ? summary : item))
        : [summary, ...projectChats];

      return {
        ...current,
        [chat.project_id]: sortChats(nextChats),
      };
    });
  }

  function findProjectIdForChat(chatId: number) {
    for (const [projectId, chats] of Object.entries(chatsByProjectId)) {
      if (chats.some((chat) => chat.id === chatId)) {
        return Number(projectId);
      }
    }
    return null;
  }

  useEffect(() => {
    let mounted = true;

    async function loadProjects() {
      try {
        setProjectsLoading(true);
        setProjectError(null);
        const data = await listProjects();
        if (!mounted) {
          return;
        }

        setProjects(data);
        const firstProjectId = data[0]?.id ?? null;
        setActiveProjectId((current) =>
          current && data.some((project) => project.id === current) ? current : firstProjectId,
        );
        setExpandedProjectIds((current) => {
          const next: Record<number, boolean> = {};
          for (const project of data) {
            next[project.id] = current[project.id] ?? project.id === firstProjectId;
          }
          return next;
        });
      } catch (error) {
        if (mounted) {
          setProjectError(error instanceof Error ? error.message : "Failed to load projects");
        }
      } finally {
        if (mounted) {
          setProjectsLoading(false);
        }
      }
    }

    loadProjects();

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!activeProjectId) {
      setPapers([]);
      setActivePaperId(null);
      setActiveChatId(null);
      setSelectedCitation(null);
      setSourcePanelOpen(false);
      return;
    }

    const projectId = activeProjectId;
    let mounted = true;

    setProjectError(null);
    setSelectedCitation(null);
    setSourcePanelOpen(false);

    async function loadPapers() {
      try {
        setPapersLoading(true);
        setPaperError(null);
        const data = await listProjectPapers(projectId);
        if (!mounted) {
          return;
        }

        setPapers(data);
        setActivePaperId((current) =>
          current && data.some((paper) => paper.id === current) ? current : data[0]?.id ?? null,
        );
      } catch (error) {
        if (mounted) {
          setPaperError(error instanceof Error ? error.message : "Failed to load papers");
        }
      } finally {
        if (mounted) {
          setPapersLoading(false);
        }
      }
    }

    async function loadChats() {
      try {
        setProjectError(null);
        const data = await listProjectChats(projectId);
        if (!mounted) {
          return;
        }

        setChatsByProjectId((current) => ({
          ...current,
          [projectId]: sortChats(data),
        }));
        setActiveChatId((current) =>
          current && data.some((chat) => chat.id === current) ? current : data[0]?.id ?? null,
        );
      } catch (error) {
        if (mounted) {
          setProjectError(error instanceof Error ? error.message : "Failed to load chats");
        }
      }
    }

    loadPapers();
    loadChats();

    return () => {
      mounted = false;
    };
  }, [activeProjectId]);

  useEffect(() => {
    if (!activeChatId) {
      return;
    }

    let mounted = true;
    const chatId = activeChatId;

    async function loadChatDetail() {
      try {
        setChatDetailLoadingId(chatId);
        setChatErrors((current) => ({ ...current, [chatId]: null }));
        const chat = await getChat(chatId);
        if (!mounted) {
          return;
        }
        upsertChat(chat);
      } catch (error) {
        if (mounted) {
          setChatErrors((current) => ({
            ...current,
            [chatId]: error instanceof Error ? error.message : "Failed to load chat",
          }));
        }
      } finally {
        if (mounted) {
          setChatDetailLoadingId((current) => (current === chatId ? null : current));
        }
      }
    }

    loadChatDetail();

    return () => {
      mounted = false;
    };
  }, [activeChatId]);

  function handleProjectSelect(projectId: number) {
    setActiveProjectId(projectId);
    setActiveChatId((current) => {
      const cachedChats = chatsByProjectId[projectId] || [];
      if (current && cachedChats.some((chat) => chat.id === current)) {
        return current;
      }
      return cachedChats[0]?.id ?? null;
    });
    setExpandedProjectIds((current) => ({ ...current, [projectId]: true }));
  }

  function handleProjectToggle(projectId: number) {
    setExpandedProjectIds((current) => ({
      ...current,
      [projectId]: !(current[projectId] ?? false),
    }));
  }

  function handleChatSelect(chatId: number) {
    const projectId = findProjectIdForChat(chatId);
    if (!projectId) {
      return;
    }

    setActiveProjectId(projectId);
    setActiveChatId(chatId);
    setExpandedProjectIds((current) => ({ ...current, [projectId]: true }));
    setSelectedCitation(null);
    setSourcePanelOpen(false);
  }

  async function handleNewChat(projectId = activeProjectId) {
    if (!projectId) {
      return;
    }

    try {
      const chat = await createProjectChat(projectId, {});
      upsertChat(chat);
      setProjectError(null);
      setDraftByChatId((current) => ({ ...current, [chat.id]: "" }));
      setActiveProjectId(projectId);
      setActiveChatId(chat.id);
      setExpandedProjectIds((current) => ({ ...current, [projectId]: true }));
      setSelectedCitation(null);
      setSourcePanelOpen(false);
    } catch (error) {
      setProjectError(error instanceof Error ? error.message : "Failed to create chat");
    }
  }

  function handleRequestDeleteProject(projectId: number) {
    const project = projects.find((item) => item.id === projectId);
    if (!project) {
      return;
    }

    setDeleteError(null);
    setDeleteTarget({ kind: "project", projectId, label: project.name });
  }

  function handleRequestDeleteChat(projectId: number, chatId: number) {
    const chat = (chatsByProjectId[projectId] || []).find((item) => item.id === chatId);
    if (!chat) {
      return;
    }

    setDeleteError(null);
    setDeleteTarget({ kind: "chat", projectId, chatId, label: chat.title });
  }

  function handleRequestDeletePaper(projectId: number, paperId: number) {
    const paper = papers.find((item) => item.id === paperId);
    if (!paper) {
      return;
    }

    setDeleteError(null);
    setDeleteTarget({
      kind: "paper",
      projectId,
      paperId,
      label: paper.title || paper.original_filename,
    });
  }

  async function handleConfirmDelete() {
    if (!deleteTarget) {
      return;
    }

    const target = deleteTarget;

    try {
      setDeleteLoading(true);
      setDeleteError(null);

      if (target.kind === "chat") {
        await deleteChatRequest(target.chatId);

        const deletedChatId = target.chatId;
        const remainingChats = (chatsByProjectId[target.projectId] || []).filter(
          (chat) => chat.id !== deletedChatId,
        );

        setChatsByProjectId((current) => ({
          ...current,
          [target.projectId]: remainingChats,
        }));
        setChatDetailsById((current) => {
          const next = { ...current };
          delete next[deletedChatId];
          return next;
        });
        setDraftByChatId((current) => {
          const next = { ...current };
          delete next[deletedChatId];
          return next;
        });
        setChatErrors((current) => {
          const next = { ...current };
          delete next[deletedChatId];
          return next;
        });
        setSubmittingChatIds((current) => {
          const next = { ...current };
          delete next[deletedChatId];
          return next;
        });

        if (selectedCitation?.chatId === deletedChatId) {
          setSelectedCitation(null);
          setSourcePanelOpen(false);
        }

        if (activeChatId === deletedChatId) {
          setActiveChatId(remainingChats[0]?.id ?? null);
        }
      }

      if (target.kind === "project") {
        await deleteProject(target.projectId);

        const deletedChatIds = (chatsByProjectId[target.projectId] || []).map((chat) => chat.id);
        const remainingProjects = projects.filter((project) => project.id !== target.projectId);

        setProjects(remainingProjects);
        setChatsByProjectId((current) => {
          const next = { ...current };
          delete next[target.projectId];
          return next;
        });
        setExpandedProjectIds((current) => {
          const next = { ...current };
          delete next[target.projectId];
          return next;
        });
        setChatDetailsById((current) => {
          const next = { ...current };
          for (const chatId of deletedChatIds) {
            delete next[chatId];
          }
          return next;
        });
        setDraftByChatId((current) => {
          const next = { ...current };
          for (const chatId of deletedChatIds) {
            delete next[chatId];
          }
          return next;
        });
        setChatErrors((current) => {
          const next = { ...current };
          for (const chatId of deletedChatIds) {
            delete next[chatId];
          }
          return next;
        });
        setSubmittingChatIds((current) => {
          const next = { ...current };
          for (const chatId of deletedChatIds) {
            delete next[chatId];
          }
          return next;
        });

        if (activeProjectId === target.projectId) {
          const nextProjectId = remainingProjects[0]?.id ?? null;
          setActiveProjectId(nextProjectId);
          setActiveChatId(null);
          setPapers([]);
          setActivePaperId(null);
        }

        if (selectedCitation && deletedChatIds.includes(selectedCitation.chatId)) {
          setSelectedCitation(null);
          setSourcePanelOpen(false);
        }
      }

      if (target.kind === "paper") {
        await deleteProjectPaper(target.projectId, target.paperId);
        const refreshedPapers = await listProjectPapers(target.projectId);
        setPapers(refreshedPapers);
        setActivePaperId((current) =>
          current && refreshedPapers.some((paper) => paper.id === current)
            ? current
            : refreshedPapers[0]?.id ?? null,
        );
      }

      setDeleteTarget(null);
    } catch (error) {
      setDeleteError(error instanceof Error ? error.message : "Delete failed");
    } finally {
      setDeleteLoading(false);
    }
  }

  async function handleCreateProject(payload: CreateProjectPayload) {
    try {
      setCreateProjectLoading(true);
      setCreateProjectError(null);
      const project = await createProject(payload);

      setProjects((current) => [project, ...current]);
      setChatsByProjectId((current) => ({ ...current, [project.id]: [] }));
      setActiveProjectId(project.id);
      setActiveChatId(null);
      setExpandedProjectIds((current) => ({ ...current, [project.id]: true }));
      setPapers([]);
      setActivePaperId(null);
      setSelectedCitation(null);
      setSourcePanelOpen(false);
      setCreateProjectOpen(false);
    } catch (error) {
      setCreateProjectError(error instanceof Error ? error.message : "Failed to create project");
    } finally {
      setCreateProjectLoading(false);
    }
  }

  async function handleSubmit() {
    const query = activeDraft.trim();
    if (!activeProjectId || !activeChatId || !activeChat || query.length < 3 || answerLoading) {
      return;
    }

    const projectId = activeProjectId;
    const chatId = activeChatId;
    const previousChat = {
      ...activeChat,
      messages: [...activeChat.messages],
    };
    const optimisticTitle =
      previousChat.messages.length === 0 || previousChat.title === NEW_CHAT_TITLE
        ? titleFromQuestion(query)
        : previousChat.title;
    const optimisticMessage: ChatMessage = {
      id: -Date.now(),
      chat_id: chatId,
      role: "user",
      content: query,
      sources: [],
      insufficient_evidence: false,
      retrieval_hits_count: 0,
      created_at: new Date().toISOString(),
    };

    setChatErrors((current) => ({ ...current, [chatId]: null }));
    setDraftByChatId((current) => ({ ...current, [chatId]: "" }));
    setSelectedCitation(null);
    setSourcePanelOpen(false);
    setSubmittingChatIds((current) => ({ ...current, [chatId]: true }));

    upsertChat({
      ...previousChat,
      title: optimisticTitle,
      updated_at: new Date().toISOString(),
      messages: [...previousChat.messages, optimisticMessage],
    });

    try {
      await askProject(projectId, {
        query,
        chat_id: chatId,
        top_k: 6,
        max_output_tokens: 500,
        temperature: 0.1,
      });
      const refreshedChat = await getChat(chatId);
      upsertChat(refreshedChat);
    } catch (error) {
      upsertChat(previousChat);
      setChatErrors((current) => ({
        ...current,
        [chatId]: error instanceof Error ? error.message : "Answer generation failed",
      }));
    } finally {
      setSubmittingChatIds((current) => ({ ...current, [chatId]: false }));
    }
  }

  async function handleUploadFiles(files: FileList | null) {
    if (!activeProjectId || !files?.length) {
      return;
    }

    const projectId = activeProjectId;
    const uploadErrors: string[] = [];
    let hasChunkedPaper = false;

    try {
      setUploading(true);
      setPaperError(null);

      for (const file of Array.from(files)) {
        try {
          const uploadedPaper = await uploadProjectPaper(projectId, file);
          await parsePaper(uploadedPaper.id);
          const chunkedPaper = await chunkPaper(uploadedPaper.id);
          hasChunkedPaper =
            hasChunkedPaper ||
            chunkedPaper.status === "chunked" ||
            chunkedPaper.status === "indexed";
        } catch (error) {
          uploadErrors.push(
            `${file.name}: ${error instanceof Error ? error.message : "Processing failed"}`,
          );
        }
      }

      if (hasChunkedPaper) {
        try {
          await indexProject(projectId);
        } catch (error) {
          uploadErrors.push(
            `Indexing failed: ${error instanceof Error ? error.message : "Index build failed"}`,
          );
        }
      }

      const data = await listProjectPapers(projectId);
      setPapers(data);
      setActivePaperId((current) =>
        current && data.some((paper) => paper.id === current) ? current : data[0]?.id ?? null,
      );

      if (uploadErrors.length > 0) {
        setPaperError(uploadErrors.join(" "));
      }
    } catch (error) {
      setPaperError(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  function handleQuickAction(action: string) {
    if (!activeChatId) {
      return;
    }

    const templates: Record<string, string> = {
      Summarize: "Summarize the main argument across the indexed papers.",
      Compare: "Compare the main defense approaches across these papers.",
      "Find Evidence": "Find evidence about the strongest limitations discussed in the papers.",
    };

    setDraftByChatId((current) => ({
      ...current,
      [activeChatId]: templates[action] || current[activeChatId] || "",
    }));
  }

  function handleDraftChange(value: string) {
    if (!activeChatId) {
      return;
    }

    setDraftByChatId((current) => ({ ...current, [activeChatId]: value }));
  }

  function handleCitationClick(messageId: number, sourceId: string) {
    if (!activeChatId || !activeChat) {
      return;
    }

    const message = activeChat.messages.find((item) => item.id === messageId);
    const source =
      message?.role === "assistant"
        ? message.sources.find((item) => item.source_id === sourceId)
        : null;

    setSelectedCitation({ chatId: activeChatId, messageId, sourceId });
    setSourcePanelOpen(true);
    if (source) {
      setActivePaperId(source.paper_id);
    }
  }

  return (
    <>
      <div className="flex h-screen min-w-[1180px] overflow-hidden bg-[var(--background)] text-slate-900">
        <AppSidebar
          projects={projects}
          activeProjectId={activeProjectId}
          activeChatId={activeChatId}
          chatsByProjectId={chatsByProjectId}
          expandedProjectIds={expandedProjectIds}
          onOpenCreateProject={() => {
            setCreateProjectError(null);
            setCreateProjectOpen(true);
          }}
          onProjectSelect={handleProjectSelect}
          onProjectToggle={handleProjectToggle}
          onChatSelect={handleChatSelect}
          onNewChat={handleNewChat}
          onDeleteProject={handleRequestDeleteProject}
          onDeleteChat={handleRequestDeleteChat}
        />

        <section className="flex min-w-0 flex-1 flex-col">
          <WorkspaceHeader
            project={activeProject}
            paperCount={papers.length}
            indexedCount={indexedCount}
            uploading={uploading}
            onUploadFiles={handleUploadFiles}
          />

          <div className="flex min-h-0 flex-1">
            <PapersPanel
              open={papersPanelOpen}
              projectName={activeProject?.name || null}
              activeProjectId={activeProjectId}
              papers={papers}
              activePaperId={activePaperId}
              loading={papersLoading || projectsLoading}
              error={paperError || null}
              onToggle={() => setPapersPanelOpen((current) => !current)}
              onPaperSelect={setActivePaperId}
              onDeletePaper={handleRequestDeletePaper}
            />

            <ChatThread
              projectName={activeProject?.name || null}
              hasProject={Boolean(activeProject)}
              hasChat={Boolean(activeChatSummary)}
              paperCount={papers.length}
              messages={activeChat?.messages || []}
              selectedCitation={selectedCitation}
              draft={activeDraft}
              loading={answerLoading || chatLoading}
              error={activeChatError || projectError}
              disabled={!activeProjectId || !activeChatId || !activeChat || projectsLoading || answerLoading}
              onDraftChange={handleDraftChange}
              onSubmit={handleSubmit}
              onCitationClick={handleCitationClick}
              onQuickAction={handleQuickAction}
              onOpenCreateProject={() => {
                setCreateProjectError(null);
                setCreateProjectOpen(true);
              }}
              onNewChat={() => handleNewChat(activeProjectId)}
            />

            <SourcesPanel
              open={sourcePanelOpen}
              sources={selectedSources}
              activeSourceId={selectedCitation?.sourceId || null}
              onClose={() => setSourcePanelOpen(false)}
              onOpen={() => setSourcePanelOpen(true)}
              onSourceSelect={(sourceId) => {
                if (selectedCitation) {
                  setSelectedCitation({ ...selectedCitation, sourceId });
                }
                const source = selectedSources.find((item) => item.source_id === sourceId);
                if (source) {
                  setActivePaperId(source.paper_id);
                }
              }}
            />
          </div>
        </section>
      </div>

      <CreateProjectModal
        open={createProjectOpen}
        loading={createProjectLoading}
        error={createProjectError}
        onClose={() => {
          if (!createProjectLoading) {
            setCreateProjectOpen(false);
            setCreateProjectError(null);
          }
        }}
        onSubmit={handleCreateProject}
      />

      <DeleteItemModal
        open={Boolean(deleteTarget)}
        title={
          deleteTarget?.kind === "project"
            ? "Delete project"
            : deleteTarget?.kind === "paper"
              ? "Delete paper"
              : "Delete chat"
        }
        itemLabel={deleteTarget?.label || ""}
        scopeLabel={
          deleteTarget?.kind === "project"
            ? "workspace"
            : deleteTarget?.kind === "paper"
              ? "project papers"
              : "project chats"
        }
        loading={deleteLoading}
        error={deleteError}
        onClose={() => {
          if (!deleteLoading) {
            setDeleteTarget(null);
            setDeleteError(null);
          }
        }}
        onConfirm={handleConfirmDelete}
      />
    </>
  );
}
