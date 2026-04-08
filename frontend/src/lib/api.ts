import { createClient } from "./supabase";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

async function authFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers: Record<string, string> = {};

  // Only spread non-FormData headers (don't override Content-Type for file uploads)
  if (options.headers) {
    Object.assign(headers, options.headers);
  }

  if (session?.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }

  const url = `${API_URL}${path}`;
  console.log(`[API] ${options.method || "GET"} ${url}`, { hasToken: !!session?.access_token });

  const res = await fetch(url, {
    ...options,
    headers,
  });

  console.log(`[API] Response: ${res.status} ${res.statusText}`);
  return res;
}

export async function uploadFile(file: File): Promise<{ file_id: string; filename: string }> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await authFetch("/api/upload", { method: "POST", body: formData });
  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
  return res.json();
}

export async function startProcessing(
  fileId: string,
  name?: string
): Promise<{ job_id: string; session_id: string }> {
  const res = await authFetch("/api/process", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_id: fileId, name }),
  });
  if (!res.ok) throw new Error(`Process failed: ${res.statusText}`);
  return res.json();
}

export interface JobStatusResponse {
  job_id: string;
  status: string;
  current_stage: string | null;
  progress: number;
  error: string | null;
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const res = await authFetch(`/api/status/${jobId}`);
  if (!res.ok) throw new Error(`Status check failed: ${res.statusText}`);
  return res.json();
}

export async function getSessions(): Promise<
  { id: string; name: string; created_at: string; status: string; groups_count: number }[]
> {
  const res = await authFetch("/api/sessions");
  if (!res.ok) throw new Error(`Sessions fetch failed: ${res.statusText}`);
  return res.json();
}

export async function getSessionOutput(sessionId: string): Promise<{
  id: string;
  name: string;
  markdown: string;
  concept_groups: unknown[] | null;
  verification_report: unknown[] | null;
}> {
  const res = await authFetch(`/api/sessions/${sessionId}`);
  if (!res.ok) throw new Error(`Session output failed: ${res.statusText}`);
  return res.json();
}
