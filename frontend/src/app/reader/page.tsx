"use client";

import { useState, useEffect, useRef } from "react";
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
  const [activeSection, setActiveSection] = useState(0);
  const sectionRefs = useRef<(HTMLDivElement | null)[]>([]);
  const rightPanelRef = useRef<HTMLDivElement | null>(null);

  const handleScroll = () => {
    const refs = sectionRefs.current;
    const threshold = window.innerHeight * 0.4;
    let newActive = 0;
    for (let i = 0; i < refs.length; i++) {
      const el = refs[i];
      if (!el) continue;
      if (el.getBoundingClientRect().top <= threshold) newActive = i;
    }
    setActiveSection(newActive);
  };

  // Auto-collapse sidebar on reader page
  useEffect(() => {
    store.setSidebarOpen(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-poll only when we have an active pipeline run for this session and are waiting for content
  const pollingSessionId = useRef<string | null>(null);
  useEffect(() => {
    if (store.markdown || !store.activeSessionId) return;
    const id = store.activeSessionId;
    // Only poll if there's a live pipeline run tracking this session
    const hasActivePipeline = Object.values(store.pipelineRuns).some(
      (r) => r.isProcessing && r.sessionId === id
    );
    if (!hasActivePipeline) return;
    pollingSessionId.current = id;
    const interval = setInterval(() => {
      if (pollingSessionId.current === id) store.loadSession(id);
    }, 15000);
    return () => {
      clearInterval(interval);
      pollingSessionId.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [store.markdown, store.activeSessionId, store.pipelineRuns]);

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

  // Empty state — only show "still processing" when we have an active pipeline run for this session
  if (!store.markdown) {
    // Find an active pipeline run for the current session (tracked this tab, not lost on refresh)
    const activePipelineRun = Object.values(store.pipelineRuns).find(
      (r) => r.isProcessing && r.sessionId === store.activeSessionId
    );
    const isActivelyProcessing = !!activePipelineRun;

    return (
      <div className="flex-1 flex items-center justify-center px-4 py-24">
        <div className="text-center max-w-md">
          <div
            className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6"
            style={{ background: "var(--accent-dim)", color: "var(--accent)" }}
          >
            {isActivelyProcessing ? (
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
            {isActivelyProcessing ? "Processing in background..." : "No lecture loaded"}
          </h2>
          <p className="text-sm mb-6" style={{ color: "var(--text-secondary)" }}>
            {isActivelyProcessing
              ? "Your lecture is being generated. View the progress or wait here — it'll appear automatically when ready."
              : "Upload a lecture recording or transcript to get started."}
          </p>
          {isActivelyProcessing ? (
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={() => router.push("/upload")}
                className="btn-glow px-6 py-3 rounded-xl text-sm font-semibold"
                style={{
                  background: "linear-gradient(135deg, var(--accent), #FF8555)",
                  color: "#fff",
                  boxShadow: "0 8px 32px var(--accent-glow)",
                }}
              >
                View progress
              </button>
            </div>
          ) : (
            <button
              onClick={() => router.push("/upload")}
              className="btn-glow px-6 py-3 rounded-xl text-sm font-semibold"
              style={{
                background: "linear-gradient(135deg, var(--accent), #FF8555)",
                color: "#fff",
                boxShadow: "0 8px 32px var(--accent-glow)",
              }}
            >
              Upload a Lecture
            </button>
          )}
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

  // V2 rendering — sticky left slide panel + scrollable right narratives
  const slideGroups: Record<number, SlideCard[]> = {};
  for (const card of slides) {
    const num = parseInt(card.slide_id.replace(/[a-z]/g, ""));
    if (!slideGroups[num]) slideGroups[num] = [];
    slideGroups[num].push(card);
  }

  const activeSession = store.sessions.find((s) => s.id === store.activeSessionId);
  const sessionName = activeSession?.name || "Untitled Lecture";

  const activeSectionData = transcript[activeSection];
  const activeSectionSlides = activeSectionData
    ? (slideGroups[activeSectionData.slide_number] || [])
    : [];

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Lightbox */}
      {lightboxSrc && (
        <ImageLightbox src={lightboxSrc} onClose={() => setLightboxSrc(null)} />
      )}

      {/* Desktop: left slide panel — stays pinned, updates as you scroll */}
      <div
        className="hidden md:flex flex-col shrink-0 overflow-y-auto"
        style={{
          width: "44%",
          padding: "32px 20px 64px 24px",
          borderRight: "1px solid var(--border)",
        }}
      >
        {/* Editable session title lives here on desktop */}
        <h1
          contentEditable
          suppressContentEditableWarning
          onBlur={async (e) => {
            const val = e.currentTarget.textContent?.trim() || "";
            if (val && val !== sessionName && store.activeSessionId) {
              const sessionId = store.activeSessionId;
              useAppStore.setState((s) => ({
                sessions: s.sessions.map((sess) =>
                  sess.id === sessionId ? { ...sess, name: val } : sess
                ),
              }));
              const { renameSession } = await import("@/lib/api");
              renameSession(sessionId, val).catch(() => store.loadSessions());
            }
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") { e.preventDefault(); e.currentTarget.blur(); }
          }}
          className="text-lg font-semibold mb-6 outline-none rounded-lg px-2 py-1 -ml-2 transition-colors"
          style={{ color: "var(--text-secondary)", cursor: "text" }}
          onMouseEnter={(e) => { e.currentTarget.style.background = "var(--bg-elevated)"; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
          onFocus={(e) => { e.currentTarget.style.background = "var(--bg-elevated)"; e.currentTarget.style.color = "var(--text-primary)"; }}
        >
          {sessionName}
        </h1>

        {/* Current section's slide(s) */}
        {activeSectionSlides.length > 0 ? (
          <SlideCardGroup cards={activeSectionSlides} onImageClick={setLightboxSrc} />
        ) : (
          <div
            className="rounded-2xl p-8 text-center border"
            style={{ background: "var(--bg-surface)", borderColor: "var(--border)" }}
          >
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>No slides for this section</p>
          </div>
        )}

        {transcript.length > 1 && (
          <p className="mt-4 text-xs" style={{ color: "var(--text-muted)" }}>
            Section {activeSection + 1} / {transcript.length}
          </p>
        )}
      </div>

      {/* Right: scrollable narratives */}
      <div
        ref={rightPanelRef}
        className="flex-1 min-w-0 overflow-y-auto"
        style={{ padding: "32px 24px 64px 32px" }}
        onScroll={handleScroll}
      >
        {/* Mobile: title at top of scroll */}
        <h1
          contentEditable
          suppressContentEditableWarning
          onBlur={async (e) => {
            const val = e.currentTarget.textContent?.trim() || "";
            if (val && val !== sessionName && store.activeSessionId) {
              const sessionId = store.activeSessionId;
              useAppStore.setState((s) => ({
                sessions: s.sessions.map((sess) =>
                  sess.id === sessionId ? { ...sess, name: val } : sess
                ),
              }));
              const { renameSession } = await import("@/lib/api");
              renameSession(sessionId, val).catch(() => store.loadSessions());
            }
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") { e.preventDefault(); e.currentTarget.blur(); }
          }}
          className="md:hidden text-lg font-semibold mb-8 outline-none rounded-lg px-2 py-1 -ml-2 transition-colors"
          style={{ color: "var(--text-secondary)", cursor: "text" }}
          onMouseEnter={(e) => { e.currentTarget.style.background = "var(--bg-elevated)"; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
          onFocus={(e) => { e.currentTarget.style.background = "var(--bg-elevated)"; e.currentTarget.style.color = "var(--text-primary)"; }}
        >
          {sessionName}
        </h1>

        {transcript.map((section, i) => (
          <div
            key={i}
            ref={(el) => { sectionRefs.current[i] = el; }}
            className="mb-12"
          >
            {/* Mobile: slide cards above narrative */}
            <div className="md:hidden mb-6">
              {(slideGroups[section.slide_number] || []).length > 0 && (
                <SlideCardGroup
                  cards={slideGroups[section.slide_number]}
                  onImageClick={setLightboxSrc}
                />
              )}
            </div>

            <NarrativeSection section={section} />

            {i < transcript.length - 1 && (
              <hr className="mt-12" style={{ borderColor: "var(--border)" }} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
