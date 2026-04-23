const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

export type Project = {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  topic_label: string | null;
  created_at: string;
};

export type Paper = {
  id: number;
  project_id: number;
  original_filename: string;
  stored_filename: string;
  title: string | null;
  authors: string | null;
  year: number | null;
  status: string;
  file_path: string;
  processed_path: string | null;
  created_at: string;
};

export type AnswerSource = {
  source_id: string;
  chunk_id: string;
  paper_id: number;
  section_heading: string | null;
  paper_title: string | null;
  original_filename: string | null;
  page_start: number;
  page_end: number;
  hybrid_score: number;
  excerpt: string;
};

export type ChatMessage = {
  id: number;
  chat_id: number;
  role: "user" | "assistant";
  content: string;
  sources: AnswerSource[];
  insufficient_evidence: boolean;
  retrieval_hits_count: number;
  created_at: string;
};

export type Chat = {
  id: number;
  project_id: number;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
};

export type ChatSummary = {
  id: number;
  project_id: number;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
};

export type AskResponse = {
  project_id: number;
  project_slug: string;
  chat_id: number | null;
  query: string;
  answer: string;
  insufficient_evidence: boolean;
  retrieval_hits_count: number;
  used_sources: AnswerSource[];
};

export type AskPayload = {
  query: string;
  chat_id?: number | null;
  top_k: number;
  max_output_tokens: number;
  temperature: number;
};

export type CreateProjectPayload = {
  name: string;
  description?: string | null;
  topic_label?: string | null;
};

export type CreateChatPayload = {
  title?: string | null;
};

export type ProjectIndexResponse = {
  project_id: number;
  project_slug: string;
  total_project_papers: number;
  total_indexed_papers: number;
  indexed_paper_ids: number[];
  total_chunks_indexed: number;
  embedding_model: string;
  chroma_collection: string;
  bm25_index_path: string;
};

async function readJsonOrThrow<T>(res: Response): Promise<T> {
  if (res.ok) {
    return res.json() as Promise<T>;
  }

  let message = `Request failed with status ${res.status}`;
  try {
    const data = await res.json();
    if (typeof data.detail === "string") {
      message = data.detail;
    }
  } catch {
    // Keep the status-based message when the response body is not JSON.
  }

  throw new Error(message);
}

async function throwIfNotOk(res: Response): Promise<void> {
  if (res.ok) {
    return;
  }

  let message = `Request failed with status ${res.status}`;
  try {
    const data = await res.json();
    if (typeof data.detail === "string") {
      message = data.detail;
    }
  } catch {
    // Keep the status-based message when the response body is not JSON.
  }

  throw new Error(message);
}

export async function getHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error("Failed to fetch health status");
  }
  return res.json();
}

export async function listProjects(): Promise<Project[]> {
  const res = await fetch(`${API_BASE}/projects`, { cache: "no-store" });
  return readJsonOrThrow<Project[]>(res);
}

export async function createProject(payload: CreateProjectPayload): Promise<Project> {
  const res = await fetch(`${API_BASE}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return readJsonOrThrow<Project>(res);
}

export async function deleteProject(projectId: number): Promise<void> {
  const res = await fetch(`${API_BASE}/projects/${projectId}`, {
    method: "DELETE",
  });
  return throwIfNotOk(res);
}

export async function listProjectChats(projectId: number): Promise<ChatSummary[]> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/chats`, {
    cache: "no-store",
  });
  return readJsonOrThrow<ChatSummary[]>(res);
}

export async function createProjectChat(
  projectId: number,
  payload: CreateChatPayload = {},
): Promise<Chat> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/chats`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return readJsonOrThrow<Chat>(res);
}

export async function getChat(chatId: number): Promise<Chat> {
  const res = await fetch(`${API_BASE}/chats/${chatId}`, {
    cache: "no-store",
  });
  return readJsonOrThrow<Chat>(res);
}

export async function deleteChat(chatId: number): Promise<void> {
  const res = await fetch(`${API_BASE}/chats/${chatId}`, {
    method: "DELETE",
  });
  return throwIfNotOk(res);
}

export async function listProjectPapers(projectId: number): Promise<Paper[]> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/papers`, {
    cache: "no-store",
  });
  return readJsonOrThrow<Paper[]>(res);
}

export async function askProject(
  projectId: number,
  payload: AskPayload,
): Promise<AskResponse> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return readJsonOrThrow<AskResponse>(res);
}

export async function uploadProjectPaper(
  projectId: number,
  file: File,
): Promise<Paper> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/projects/${projectId}/papers/upload`, {
    method: "POST",
    body: formData,
  });
  return readJsonOrThrow<Paper>(res);
}

export async function deleteProjectPaper(projectId: number, paperId: number): Promise<void> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/papers/${paperId}`, {
    method: "DELETE",
  });
  return throwIfNotOk(res);
}

export async function parsePaper(paperId: number): Promise<Paper> {
  const res = await fetch(`${API_BASE}/papers/${paperId}/parse`, {
    method: "POST",
  });
  return readJsonOrThrow<Paper>(res);
}

export async function chunkPaper(paperId: number): Promise<Paper> {
  const res = await fetch(`${API_BASE}/papers/${paperId}/chunk`, {
    method: "POST",
  });
  return readJsonOrThrow<Paper>(res);
}

export async function indexProject(projectId: number): Promise<ProjectIndexResponse> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/index`, {
    method: "POST",
  });
  return readJsonOrThrow<ProjectIndexResponse>(res);
}
