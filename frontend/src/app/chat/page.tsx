"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";
import ChatInput from "@/components/chat-ui/ChatInput";
import SuggestedActions from "@/components/chat-ui/SuggestedActions";
import { SlideCardGroup } from "@/components/SlideCard";
import NarrativeSection from "@/components/NarrativeSection";
import ImageLightbox from "@/components/ImageLightbox";
import type { SlideCard, TranscriptSection } from "@/lib/types";

// ─── Pipeline stage progress as "thinking" bubbles ────────────────────────────
function ThinkingBubble({ stages, currentStageIndex, subProgress, isUploading, uploadProgress }: {
  stages: { name: string; status: string }[];
  currentStageIndex: number;
  subProgress: number;
  isUploading: boolean;
  uploadProgress: number;
}) {
  return (
    <div className="flex gap-3 items-start max-w-3xl mx-auto">
      {/* Klare avatar */}
      <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0 mt-0.5"
        style={{ background: "var(--accent-dim)", border: "1px solid rgba(255,107,53,0.2)" }}>
        <img src="/brand/logo-mark-dark.svg" alt="Klare" className="w-4 h-4" onError={(e) => {
          (e.target as HTMLImageElement).style.display = "none";
          (e.target as HTMLImageElement).parentElement!.innerHTML = `<span style="color:var(--accent);font-size:10px;font-weight:700">K</span>`;
        }} />
      </div>

      <div className="flex-1 min-w-0 pt-1">
        <p className="text-xs font-semibold mb-3" style={{ color: "var(--text-muted)" }}>Klare</p>

        {isUploading ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full border-2 border-t-transparent animate-spin shrink-0"
                style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }} />
              <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
                Uploading lecture... {uploadProgress}%
              </span>
            </div>
            <div className="h-1 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.06)", maxWidth: "300px" }}>
              <div className="h-full rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress}%`, background: "linear-gradient(90deg, var(--accent), #FF8555)" }} />
            </div>
          </div>
        ) : (
          <div className="space-y-2.5">
            {stages.map((stage, i) => (
              <div key={i} className="flex items-center gap-2.5">
                {stage.status === "done" ? (
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#4ade80" strokeWidth="2.5" strokeLinecap="round" className="shrink-0">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : stage.status === "running" ? (
                  <div className="w-3 h-3 rounded-full border-2 border-t-transparent animate-spin shrink-0"
                    style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }} />
                ) : (
                  <div className="w-3 h-3 rounded-full shrink-0" style={{ background: "rgba(255,255,255,0.1)" }} />
                )}
                <span
                  className="text-sm transition-colors"
                  style={{
                    color: stage.status === "done"
                      ? "var(--text-muted)"
                      : stage.status === "running"
                        ? "var(--text-primary)"
                        : "rgba(255,255,255,0.2)",
                  }}
                >
                  {stage.name}
                  {stage.status === "running" && i === currentStageIndex && subProgress > 0 && (
                    <span className="ml-2 text-xs" style={{ color: "var(--accent)" }}>{subProgress}%</span>
                  )}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── User's uploaded file as a "message" ──────────────────────────────────────
function UserFileBubble({ fileName, fileType }: { fileName: string; fileType: "video" | "transcript" }) {
  return (
    <div className="flex justify-end max-w-3xl mx-auto">
      <div
        className="flex items-center gap-2.5 px-4 py-3 rounded-2xl text-sm max-w-xs"
        style={{
          background: "rgba(255,107,53,0.12)",
          border: "1px solid rgba(255,107,53,0.2)",
        }}
      >
        {fileType === "video" ? (
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round">
            <polygon points="23 7 16 12 23 17 23 7" />
            <rect x="1" y="5" width="15" height="14" rx="2" />
          </svg>
        ) : (
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
        )}
        <span className="truncate font-medium" style={{ color: "var(--text-primary)" }}>{fileName}</span>
      </div>
    </div>
  );
}

// ─── Lecture reader as inline "response" ──────────────────────────────────────
function LectureResponse({ markdown }: { markdown: string }) {
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);
  const [slides, setSlides] = useState<SlideCard[]>([]);
  const [transcript, setTranscript] = useState<TranscriptSection[]>([]);
  const [isV2, setIsV2] = useState(false);
  const [legacyMarkdown, setLegacyMarkdown] = useState("");

  useEffect(() => {
    if (markdown.trim().startsWith("{")) {
      try {
        const parsed = JSON.parse(markdown);
        setSlides(parsed.slides || []);
        setTranscript(parsed.transcript || []);
        setIsV2(true);
        return;
      } catch { /* fall through */ }
    }
    setLegacyMarkdown(markdown);
    setIsV2(false);
  }, [markdown]);

  const slideGroups: Record<number, SlideCard[]> = {};
  for (const card of slides) {
    const num = parseInt(card.slide_id.replace(/[a-z]/g, ""));
    if (!slideGroups[num]) slideGroups[num] = [];
    slideGroups[num].push(card);
  }

  return (
    <div className="flex gap-3 items-start max-w-3xl mx-auto">
      {lightboxSrc && <ImageLightbox src={lightboxSrc} onClose={() => setLightboxSrc(null)} />}

      {/* Klare avatar */}
      <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0 mt-0.5"
        style={{ background: "var(--accent-dim)", border: "1px solid rgba(255,107,53,0.2)" }}>
        <span style={{ color: "var(--accent)", fontSize: "11px", fontWeight: 700 }}>K</span>
      </div>

      <div className="flex-1 min-w-0 pt-1">
        <p className="text-xs font-semibold mb-4" style={{ color: "var(--text-muted)" }}>Klare</p>

        <div
          className="rounded-2xl overflow-hidden"
          style={{ border: "1px solid rgba(255,255,255,0.07)", background: "rgba(255,255,255,0.02)" }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-3.5"
            style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
            <div className="flex items-center gap-2">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4ade80" strokeWidth="2.5" strokeLinecap="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                Lecture ready
              </span>
            </div>
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              {isV2 ? `${transcript.length} sections` : "Legacy format"}
            </span>
          </div>

          {/* Content */}
          <div className="max-h-[70vh] overflow-y-auto">
            {isV2 ? (
              <div className="p-5 space-y-10">
                {transcript.map((section, i) => {
                  const sectionSlides = slideGroups[section.slide_number] || [];
                  return (
                    <div key={i}>
                      <div className="hidden md:grid gap-8" style={{ gridTemplateColumns: "1fr 1fr" }}>
                        <div className="sticky top-4 self-start space-y-4">
                          {sectionSlides.length > 0 ? (
                            <SlideCardGroup cards={sectionSlides} onImageClick={setLightboxSrc} />
                          ) : (
                            <div className="rounded-xl p-6 text-center" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
                              <p className="text-xs" style={{ color: "var(--text-muted)" }}>No slides</p>
                            </div>
                          )}
                        </div>
                        <div className="pl-6 border-l" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                          <NarrativeSection section={section} />
                        </div>
                      </div>
                      <div className="md:hidden space-y-4">
                        {sectionSlides.length > 0 && <SlideCardGroup cards={sectionSlides} onImageClick={setLightboxSrc} />}
                        <NarrativeSection section={section} />
                      </div>
                      {i < transcript.length - 1 && (
                        <hr className="mt-8" style={{ borderColor: "rgba(255,255,255,0.05)" }} />
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="p-5 prose prose-invert prose-sm max-w-none">
                <pre className="whitespace-pre-wrap text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                  {legacyMarkdown}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Main page ─────────────────────────────────────────────────────────────────
export default function ChatPage() {
  const {
    user, markdown, activeSessionId, sessions,
    transcriptFile, videoFile,
    stages, currentStageIndex, subProgress,
    isProcessing, isDone, pipelineError,
    isUploading, uploadProgress,
    startPipeline, loadSession,
  } = useAppStore();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const hasFile = !!(transcriptFile || videoFile);
  const hasStarted = isProcessing || isDone || isUploading || !!pipelineError;
  const activeSession = sessions.find((s) => s.id === activeSessionId);

  // Auto-scroll on new content
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [stages, currentStageIndex, isDone, markdown]);

  // Auto-poll when session exists but no markdown yet (e.g. after page reload)
  const pollingRef = useRef<string | null>(null);
  useEffect(() => {
    if (markdown || !activeSessionId) return;
    pollingRef.current = activeSessionId;
    const interval = setInterval(() => {
      if (pollingRef.current === activeSessionId) loadSession(activeSessionId);
    }, 15000);
    return () => { clearInterval(interval); pollingRef.current = null; };
  }, [markdown, activeSessionId]);

  const handleSubmit = () => {
    if (!hasFile || isProcessing) return;
    startPipeline();
  };

  // ── Empty state ───────────────────────────────────────────────────────────
  if (!hasStarted && !markdown) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex-1 flex flex-col items-center justify-center px-6 pb-32">
          <h1 className="text-3xl font-bold mb-2 text-center" style={{ color: "var(--text-primary)" }}>
            Hi, {user.name.split(" ")[0] || "there"} 👋
          </h1>
          <p className="text-sm mb-10 text-center" style={{ color: "var(--text-muted)" }}>
            Drop your lecture and I'll teach it back to you properly.
          </p>
          <ChatInput onSubmit={handleSubmit} />
          <SuggestedActions />
        </div>
      </div>
    );
  }

  // ── Active / done state ───────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full">
      {/* Conversation title */}
      {activeSession && (
        <div className="px-6 py-3 shrink-0" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
          <p className="text-sm font-medium truncate" style={{ color: "var(--text-secondary)" }}>
            {activeSession.name}
          </p>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-8 space-y-8">
        {/* User file bubble */}
        {(transcriptFile || videoFile) && (
          <UserFileBubble
            fileName={(transcriptFile || videoFile)!.name}
            fileType={videoFile ? "video" : "transcript"}
          />
        )}

        {/* Pipeline stages as thinking bubble */}
        {(isProcessing || isUploading) && (
          <ThinkingBubble
            stages={stages}
            currentStageIndex={currentStageIndex}
            subProgress={subProgress}
            isUploading={isUploading}
            uploadProgress={uploadProgress}
          />
        )}

        {/* Error */}
        {pipelineError && (
          <div className="flex gap-3 items-start max-w-3xl mx-auto">
            <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: "rgba(255,68,68,0.1)", border: "1px solid rgba(255,68,68,0.2)" }}>
              <span style={{ color: "#FF4444", fontSize: "11px", fontWeight: 700 }}>!</span>
            </div>
            <div className="pt-1">
              <p className="text-xs font-semibold mb-1" style={{ color: "var(--text-muted)" }}>Error</p>
              <p className="text-sm" style={{ color: "#FF6666" }}>{pipelineError}</p>
              <button
                onClick={() => useAppStore.getState().reset()}
                className="mt-3 text-xs px-3 py-1.5 rounded-lg transition-colors"
                style={{ background: "rgba(255,255,255,0.06)", color: "var(--text-secondary)", border: "1px solid rgba(255,255,255,0.08)" }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.1)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.06)")}
              >
                Try again
              </button>
            </div>
          </div>
        )}

        {/* Lecture response */}
        {isDone && markdown && <LectureResponse markdown={markdown} />}

        {/* Still processing (after reload) */}
        {!isProcessing && !isDone && !pipelineError && activeSessionId && !markdown && (
          <div className="flex gap-3 items-start max-w-3xl mx-auto">
            <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: "var(--accent-dim)", border: "1px solid rgba(255,107,53,0.2)" }}>
              <span style={{ color: "var(--accent)", fontSize: "11px", fontWeight: 700 }}>K</span>
            </div>
            <div className="pt-1 flex items-center gap-2">
              <div className="w-3 h-3 rounded-full border-2 border-t-transparent animate-spin"
                style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }} />
              <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                Still generating — checking every 15s...
              </p>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Sticky input at bottom (when not processing) */}
      {!isProcessing && !isUploading && (
        <div className="shrink-0 px-6 pb-6 pt-2">
          {isDone ? (
            <div className="max-w-3xl mx-auto">
              <button
                onClick={() => { useAppStore.getState().reset(); }}
                className="w-full py-3 rounded-2xl text-sm font-medium transition-all"
                style={{
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(255,255,255,0.08)",
                  color: "var(--text-secondary)",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "rgba(255,255,255,0.07)";
                  e.currentTarget.style.color = "var(--text-primary)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "rgba(255,255,255,0.04)";
                  e.currentTarget.style.color = "var(--text-secondary)";
                }}
              >
                + New lecture
              </button>
            </div>
          ) : (
            <ChatInput onSubmit={handleSubmit} disabled={isProcessing} />
          )}
        </div>
      )}
    </div>
  );
}
