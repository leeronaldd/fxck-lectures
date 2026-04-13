"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";
import { SlideCardGroup } from "@/components/SlideCard";
import NarrativeSection from "@/components/NarrativeSection";
import ImageLightbox from "@/components/ImageLightbox";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import type { SlideCard, TranscriptSection } from "@/lib/types";

export default function ReaderPage() {
  const router = useRouter();
  const store = useAppStore();

  const [loading, setLoading] = useState(true);
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);
  const [slides, setSlides] = useState<SlideCard[]>([]);
  const [transcript, setTranscript] = useState<TranscriptSection[]>([]);
  const [isV2, setIsV2] = useState(false);
  const [legacyMarkdown, setLegacyMarkdown] = useState("");

  // Auto-collapse sidebar on reader page
  useEffect(() => {
    store.setSidebarOpen(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load data — detect V2 JSON vs legacy markdown
  useEffect(() => {
    if (store.markdown) {
      // V2: markdown field contains JSON string
      if (store.markdown.trim().startsWith("{")) {
        try {
          const parsed = JSON.parse(store.markdown);
          setSlides(parsed.slides || []);
          setTranscript(parsed.transcript || []);
          setIsV2(true);
        } catch {
          // JSON parse failed — treat as legacy markdown
          setLegacyMarkdown(store.markdown);
          setIsV2(false);
        }
      } else {
        // Legacy markdown from V1
        setLegacyMarkdown(store.markdown);
        setIsV2(false);
      }
    }
    setLoading(false);
  }, [store.markdown]);

  if (loading) {
    return (
      <div className="flex-1 min-w-0">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-8 pb-16">
          {/* Skeleton: mimics the real split-view layout */}
          {[1, 2, 3].map((n) => (
            <div key={n} className="mb-12">
              <div className="hidden md:grid gap-8" style={{ gridTemplateColumns: "1fr 1fr" }}>
                {/* Left: slide card skeleton */}
                <div className="space-y-3">
                  <div className="rounded-2xl overflow-hidden border animate-pulse" style={{ background: "var(--bg-surface)", borderColor: "var(--border)" }}>
                    <div className="px-4 py-3 flex items-center gap-2 border-b" style={{ borderColor: "var(--border)" }}>
                      <div className="h-5 w-12 rounded-md" style={{ background: "var(--bg-elevated)" }} />
                      <div className="h-4 w-32 rounded" style={{ background: "var(--bg-elevated)" }} />
                    </div>
                    <div className="px-3 py-3">
                      <div className="w-full rounded-xl" style={{ background: "var(--bg-elevated)", height: "180px" }} />
                    </div>
                  </div>
                </div>
                {/* Right: narrative skeleton */}
                <div className="pl-8 border-l animate-pulse" style={{ borderColor: "var(--border)" }}>
                  <div className="h-6 w-48 rounded mb-6" style={{ background: "var(--bg-elevated)" }} />
                  <div className="space-y-3">
                    <div className="h-4 w-full rounded" style={{ background: "var(--bg-elevated)" }} />
                    <div className="h-4 w-[90%] rounded" style={{ background: "var(--bg-elevated)" }} />
                    <div className="h-4 w-[95%] rounded" style={{ background: "var(--bg-elevated)" }} />
                    <div className="h-4 w-[80%] rounded" style={{ background: "var(--bg-elevated)" }} />
                    <div className="h-4 w-0" />
                    <div className="h-4 w-full rounded" style={{ background: "var(--bg-elevated)" }} />
                    <div className="h-4 w-[85%] rounded" style={{ background: "var(--bg-elevated)" }} />
                  </div>
                </div>
              </div>
              {/* Mobile skeleton */}
              <div className="md:hidden space-y-4 animate-pulse">
                <div className="rounded-2xl border" style={{ background: "var(--bg-surface)", borderColor: "var(--border)", height: "200px" }} />
                <div className="space-y-3">
                  <div className="h-5 w-40 rounded" style={{ background: "var(--bg-elevated)" }} />
                  <div className="h-4 w-full rounded" style={{ background: "var(--bg-elevated)" }} />
                  <div className="h-4 w-[90%] rounded" style={{ background: "var(--bg-elevated)" }} />
                  <div className="h-4 w-[80%] rounded" style={{ background: "var(--bg-elevated)" }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Empty state — check if there's an active session (might still be processing)
  if (!store.markdown) {
    const hasActiveSession = !!store.activeSessionId;
    return (
      <div className="flex-1 flex items-center justify-center px-4 py-24">
        <div className="text-center max-w-md">
          <div
            className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6"
            style={{ background: "var(--accent-dim)", color: "var(--accent)" }}
          >
            {hasActiveSession ? (
              <div
                className="w-7 h-7 rounded-full border-2 border-t-transparent animate-spin"
                style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}
              />
            ) : (
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                <polyline points="14,2 14,8 20,8" />
              </svg>
            )}
          </div>
          <h2 className="text-xl font-bold mb-2" style={{ color: "var(--text-primary)" }}>
            {hasActiveSession ? "Still processing..." : "No lecture loaded"}
          </h2>
          <p className="text-sm mb-6" style={{ color: "var(--text-secondary)" }}>
            {hasActiveSession
              ? "This lecture is still being generated. It will appear here when ready — try refreshing in a minute."
              : "Upload a lecture recording or transcript to get started."}
          </p>
          <button
            onClick={() => hasActiveSession ? window.location.reload() : router.push("/upload")}
            className="btn-glow px-6 py-3 rounded-xl text-sm font-semibold"
            style={{
              background: "linear-gradient(135deg, var(--accent), #FF8555)",
              color: "#fff",
              boxShadow: "0 8px 32px var(--accent-glow)",
            }}
          >
            {hasActiveSession ? "Refresh" : "Upload a Lecture"}
          </button>
        </div>
      </div>
    );
  }

  // Legacy V1 rendering
  if (!isV2) {
    return (
      <div className="flex flex-1 overflow-x-hidden">
        <div className="flex-1 min-w-0 overflow-x-hidden">
          <div className="max-w-[1200px] mx-auto px-6 lg:px-20 py-8 pb-16 overflow-hidden">
            <MarkdownRenderer content={legacyMarkdown} />
          </div>
        </div>
      </div>
    );
  }

  // V2 rendering — slides + transcript split view
  // Group slides by slide_number for card groups (1a, 1b, etc.)
  const slideGroups: Record<number, SlideCard[]> = {};
  for (const card of slides) {
    const num = parseInt(card.slide_id.replace(/[a-z]/g, ""));
    if (!slideGroups[num]) slideGroups[num] = [];
    slideGroups[num].push(card);
  }

  // Get current session name for the editable title
  const activeSession = store.sessions.find((s) => s.id === store.activeSessionId);
  const sessionName = activeSession?.name || "Untitled Lecture";

  return (
    <div className="flex flex-1 overflow-x-hidden">
      {/* Lightbox */}
      {lightboxSrc && (
        <ImageLightbox src={lightboxSrc} onClose={() => setLightboxSrc(null)} />
      )}

      <div className="flex-1 min-w-0 overflow-y-auto">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-8 pb-16">
          {/* Editable session title */}
          <h1
            contentEditable
            suppressContentEditableWarning
            onBlur={async (e) => {
              const val = e.currentTarget.textContent?.trim() || "";
              if (val && val !== sessionName && store.activeSessionId) {
                const sessionId = store.activeSessionId;
                // Optimistically update store synchronously so React re-renders
                // with the NEW name — prevents the DOM from reverting before the API call completes
                // Optimistically update store synchronously
                useAppStore.setState((s) => ({
                  sessions: s.sessions.map((sess) =>
                    sess.id === sessionId ? { ...sess, name: val } : sess
                  ),
                }));
                // Call API in background without awaiting — it will sync on next session load
                // Awaiting here and then calling loadSessions() can still race and revert the name
                const { renameSession } = await import("@/lib/api");
                renameSession(sessionId, val).catch((err) => {
                  console.error("Failed to rename session:", err);
                  // Optionally reload on error to restore server state
                  store.loadSessions();
                });
              }
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") { e.preventDefault(); e.currentTarget.blur(); }
            }}
            className="text-lg font-semibold mb-8 outline-none rounded-lg px-2 py-1 -ml-2 transition-colors"
            style={{
              color: "var(--text-secondary)",
              cursor: "text",
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = "var(--bg-elevated)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
            onFocus={(e) => { e.currentTarget.style.background = "var(--bg-elevated)"; e.currentTarget.style.color = "var(--text-primary)"; }}
          >
            {sessionName}
          </h1>
          {transcript.map((section, i) => {
            const sectionSlides = slideGroups[section.slide_number] || [];

            return (
              <div key={i} className="mb-12">
                {/* Desktop: 50/50 split */}
                <div className="hidden md:grid gap-8" style={{ gridTemplateColumns: "1fr 1fr" }}>
                  {/* Left: slide cards */}
                  <div className="sticky top-4 self-start space-y-4">
                    {sectionSlides.length > 0 ? (
                      <SlideCardGroup cards={sectionSlides} onImageClick={setLightboxSrc} />
                    ) : (
                      <div
                        className="rounded-2xl p-8 text-center border"
                        style={{ background: "var(--bg-surface)", borderColor: "var(--border)" }}
                      >
                        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                          No slides for this section
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Right: narrative */}
                  <div className="pl-8 border-l" style={{ borderColor: "var(--border)" }}>
                    <NarrativeSection section={section} />
                  </div>
                </div>

                {/* Mobile: stacked */}
                <div className="md:hidden space-y-6">
                  {sectionSlides.length > 0 && (
                    <SlideCardGroup cards={sectionSlides} onImageClick={setLightboxSrc} />
                  )}
                  <NarrativeSection section={section} />
                </div>

                {/* Section divider */}
                {i < transcript.length - 1 && (
                  <hr className="mt-12" style={{ borderColor: "var(--border)" }} />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
