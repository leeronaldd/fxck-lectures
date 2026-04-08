import { createClient } from "./supabase";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

async function getToken(): Promise<string> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token || "";
}

export async function uploadFile(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<{ file_id: string; filename: string }> {
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

export interface PipelineEvent {
  status: string;
  current_stage: string | null;
  progress: number;
  error: string | null;
  output: {
    markdown: string;
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
export function runPipeline(
  fileId: string,
  onUpdate: (event: PipelineEvent) => void,
  onError: (error: string) => void,
  onDone: (output: PipelineEvent["output"]) => void,
): () => void {
  let cancelled = false;

  (async () => {
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/api/run/${fileId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        onError(`Pipeline failed: ${res.statusText}`);
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
      if (!cancelled) {
        onError(e instanceof Error ? e.message : "Connection lost");
      }
    }
  })();

  return () => { cancelled = true; };
}
