import { createClient } from "./supabase";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");
if (typeof window !== "undefined") {
  console.log("[API] URL:", API_URL);
}

async function getToken(): Promise<string> {
  try {
    const supabase = createClient();
    const { data: { session }, error } = await supabase.auth.getSession();
    if (error) {
      console.error("[Auth] getSession error:", error.message);
      return "";
    }
    console.log("[Auth] Got token, length:", session?.access_token?.length || 0);
    return session?.access_token || "";
  } catch (e) {
    console.error("[Auth] getToken crashed:", e);
    return "";
  }
}

const MAX_UPLOAD_MB = 100; // Cloud Run HTTP/2 supports up to 10 GiB

export async function uploadFile(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<{ file_id: string; filename: string }> {
  const sizeMB = file.size / (1024 * 1024);
  if (sizeMB > MAX_UPLOAD_MB) {
    throw new Error(`File too large (${sizeMB.toFixed(0)} MB). Maximum is ${MAX_UPLOAD_MB} MB.`);
  }

  const token = await getToken();
  console.log("[Upload] Starting upload, token length:", token.length, "file:", file.name, file.size);

  if (onProgress) onProgress(10);

  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_URL}/api/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });

  if (onProgress) onProgress(90);
  console.log("[Upload] Response:", res.status, res.statusText);

  if (!res.ok) {
    const body = await res.text();
    console.error("[Upload] Error body:", body);
    throw new Error(`Upload failed: ${res.status} ${res.statusText}`);
  }

  if (onProgress) onProgress(100);
  return res.json();
}

export async function uploadSlides(
  fileId: string,
  file: File,
): Promise<void> {
  const token = await getToken();
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_URL}/api/upload-slides?file_id=${fileId}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });

  if (!res.ok) {
    const body = await res.text();
    console.error("[Slides Upload] Error:", body);
    throw new Error(`Slides upload failed: ${res.status}`);
  }
}

export interface PipelineEvent {
  status: string;
  current_stage: string | null;
  progress: number;
  error: string | null;
  output: {
    markdown: string;
    slides: { slide_id: string; title: string; card_type: string; image_ref: string; bullet_points: string[]; exam_tip: string; ei_percent: number }[];
    transcript: { slide_number: number; title: string; narrative: string; ei_percent: number; ei_reasoning: string }[];
    concept_groups: unknown[];
    verification_report: unknown[];
  } | null;
}

/**
 * Run the pipeline via SSE stream. The backend runs the pipeline synchronously
 * inside the SSE connection, so Cloud Run stays alive for the entire duration.
 *
 * Returns a cancel function.
 */
export async function fetchSessions(): Promise<{ id: string; name: string; created_at: string }[]> {
  const token = await getToken();
  const res = await fetch(`${API_URL}/api/sessions`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchSession(sessionId: string): Promise<{
  id: string;
  name: string;
  markdown: string;
  concept_groups: unknown[];
  verification_report: unknown[];
} | null> {
  const token = await getToken();
  const res = await fetch(`${API_URL}/api/sessions/${sessionId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchProfile(): Promise<Record<string, string> | null> {
  const token = await getToken();
  const res = await fetch(`${API_URL}/api/profile`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return null;
  const data = await res.json();
  return Object.keys(data).length > 0 ? data : null;
}

export async function updateProfile(profile: Record<string, string>): Promise<boolean> {
  const token = await getToken();
  const res = await fetch(`${API_URL}/api/profile`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(profile),
  });
  return res.ok;
}

export async function createCheckoutSession(period: "monthly" | "yearly"): Promise<string | null> {
  const token = await getToken();
  const res = await fetch(`${API_URL}/api/checkout`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ period }),
  });
  if (!res.ok) return null;
  const data = await res.json();
  return data.url;
}

export async function createSession(name: string = "New Lecture"): Promise<{ id: string; name: string } | null> {
  const token = await getToken();
  const res = await fetch(`${API_URL}/api/sessions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) return null;
  return res.json();
}

export async function renameSession(sessionId: string, name: string): Promise<boolean> {
  const token = await getToken();
  const res = await fetch(`${API_URL}/api/sessions/${sessionId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name }),
  });
  return res.ok;
}

export async function deleteSession(sessionId: string): Promise<boolean> {
  const token = await getToken();
  const res = await fetch(`${API_URL}/api/sessions/${sessionId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  return res.ok;
}

export function runPipeline(
  fileId: string,
  onUpdate: (event: PipelineEvent) => void,
  onError: (error: string) => void,
  onDone: (output: PipelineEvent["output"]) => void,
  sessionId?: string,
): () => void {
  let cancelled = false;
  const controller = new AbortController();

  (async () => {
    try {
      const token = await getToken();
      const url = sessionId
        ? `${API_URL}/api/run/${fileId}?session_id=${sessionId}`
        : `${API_URL}/api/run/${fileId}`;
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
        signal: controller.signal,
      });

      if (!res.ok) {
        if (res.status === 403) {
          const body = await res.json().catch(() => ({ detail: "Usage limit reached" }));
          onError(body.detail || "You've used your free lecture. Upgrade for unlimited access.");
        } else {
          onError(`Pipeline failed: ${res.statusText}`);
        }
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        onError("No response body");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (!cancelled) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const part of parts) {
          if (part.startsWith("data: ")) {
            const data = JSON.parse(part.slice(6)) as PipelineEvent;
            onUpdate(data);

            if (data.status === "done") {
              onDone(data.output);
              return;
            }
            if (data.status === "error") {
              onError(data.error || "Pipeline failed");
              return;
            }
          }
        }
      }
    } catch (e) {
      if (!cancelled && !(e instanceof DOMException && e.name === "AbortError")) {
        onError(e instanceof Error ? e.message : "Connection lost");
      }
    }
  })();

  return () => {
    cancelled = true;
    controller.abort();
  };
}
