"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";
import { SlideCardGroup } from "@/components/SlideCard";
import NarrativeSection from "@/components/NarrativeSection";
import ImageLightbox from "@/components/ImageLightbox";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import type { SlideCard, TranscriptSection } from "@/lib/types";
import { downloadSlidesPDF, downloadTranscriptPDF } from "@/lib/pdf";

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

  // Derive the current session row (carries status from Supabase) for use
  // in both the polling effect below and the empty-state branch.
  const activeSession = store.sessions.find((s) => s.id === store.activeSessionId);
  const sessionStatus = activeSession?.status;

  // Auto-poll while we're waiting for content. Two triggers, either is enough:
  //   1. There's a live pipeline run in this tab (legacy behavior).
  //   2. Supabase says the session is still 'processing' (survives refresh).
  // This means even a user who refreshes mid-run keeps seeing the spinner
  // and gets the result automatically when the background pipeline finishes.
  const pollingSessionId = useRef<string | null>(null);
  useEffect(() => {
    if (store.markdown || !store.activeSessionId) return;
    const id = store.activeSessionId;
    const hasActivePipeline = Object.values(store.pipelineRuns).some(
      (r) => r.isProcessing && r.sessionId === id
    );
    const isServerProcessing = sessionStatus === "processing" || sessionStatus === "pending";
    if (!hasActivePipeline && !isServerProcessing) return;
    pollingSessionId.current = id;
    const interval = setInterval(() => {
      if (pollingSessionId.current === id) store.loadSession(id);
    }, 15000);
    return () => {
      clearInterval(interval);
      pollingSessionId.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [store.markdown, store.activeSessionId, store.pipelineRuns, sessionStatus]);

  // Pull streaming state from any in-flight pipeline run bound to this session.
  // When the pipeline is mid-run, we render the sections as they arrive; once
  // 'done' fires, the canonical markdown takes over with the full assembled
  // output (including completeness-checker patches applied at the end).
  const streamingRun = Object.values(store.pipelineRuns).find(
    (r) => r.sessionId === store.activeSessionId && r.isProcessing
  );
  const streamingSlides = streamingRun?.streamingSlides ?? [];
  const streamingTranscript = streamingRun?.streamingTranscript ?? [];
  const hasStreamingContent = streamingTranscript.length > 0;

  // Load data — detect V2 JSON vs legacy markdown
  useEffect(() => {
    if (store.markdown) {
      // V2: markdown field contains JSON string
      if (store.markdown.trim().startsWith("{")) {
        try {
          const parsed = JSON.parse(store.markdown);
          setSlides((parsed.slides || []).filter(Boolean));
          setTranscript((parsed.transcript || []).filter(Boolean));
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
      setLoading(false);
    } else if (hasStreamingContent) {
      // Mid-pipeline: render whatever has streamed in so far
      setSlides(streamingSlides);
      setTranscript(streamingTranscript);
      setIsV2(true);
      setLoading(false);
    } else {
      setLoading(false);
    }
  }, [store.markdown, hasStreamingContent, streamingSlides, streamingTranscript]);

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

  // Empty state — three branches:
  //   1. failed   → error + retry button (status from Supabase, survives refresh)
  //   2. processing/pending → spinner + ETA (live pipeline run OR server status)
  //   3. idle     → "no lecture loaded" + upload CTA
  if (!store.markdown && !hasStreamingContent) {
    const activePipelineRun = Object.values(store.pipelineRuns).find(
      (r) => r.isProcessing && r.sessionId === store.activeSessionId
    );
    const isFailed = sessionStatus === "failed";
    const isActivelyProcessing =
      !!activePipelineRun || sessionStatus === "processing" || sessionStatus === "pending";

    if (isFailed) {
      return (
        <div className="flex-1 flex items-center justify-center px-4 py-24">
          <div className="text-center max-w-md">
            <div
              className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6"
              style={{ background: "rgba(239, 68, 68, 0.12)", color: "#ef4444" }}
            >
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <h2 className="text-xl font-bold mb-2" style={{ color: "var(--text-primary)" }}>
              Generation failed
            </h2>
            <p className="text-sm mb-2" style={{ color: "var(--text-secondary)" }}>
              Something went wrong while building this lecture. Your other lectures are unaffected.
            </p>
            {activeSession?.errorMessage ? (
              <p
                className="text-xs mb-6 font-mono px-3 py-2 rounded-lg text-left"
                style={{ background: "var(--bg-elevated)", color: "var(--text-secondary)" }}
              >
                {activeSession.errorMessage}
              </p>
            ) : (
              <div className="mb-6" />
            )}
            <button
              onClick={() => router.push("/upload")}
              className="btn-glow px-6 py-3 rounded-xl text-sm font-semibold"
              style={{
                background: "linear-gradient(135deg, var(--accent), #FF8555)",
                color: "#fff",
                boxShadow: "0 8px 32px var(--accent-glow)",
              }}
            >
              Try again
            </button>
          </div>
        </div>
      );
    }

    // Check if a server-side "processing" session has been stuck too long (no live pipeline in this tab)
    const isStale = (() => {
      if (!activeSession?.createdAt || !!activePipelineRun) return false;
      if (sessionStatus !== "processing" && sessionStatus !== "pending") return false;
      const ageMs = Date.now() - new Date(activeSession.createdAt).getTime();
      // Our typical run is ~3-5 min. 15 min gives headroom for slow
      // transcriptions before we flag the session as stuck.
      return ageMs > 15 * 60 * 1000;
    })();

    return (
      <div className="flex-1 flex items-center justify-center px-4 py-24">
        <div className="text-center max-w-md">
          <div
            className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6"
            style={{ background: isStale ? "rgba(251, 191, 36, 0.12)" : "var(--accent-dim)", color: isStale ? "#fbbf24" : "var(--accent)" }}
          >
            {isActivelyProcessing ? (
              <div
                className="w-7 h-7 rounded-full border-2 border-t-transparent animate-spin"
                style={{ borderColor: isStale ? "#fbbf24" : "var(--accent)", borderTopColor: "transparent" }}
              />
            ) : (
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                <polyline points="14,2 14,8 20,8" />
              </svg>
            )}
          </div>
          <h2 className="text-xl font-bold mb-2" style={{ color: "var(--text-primary)" }}>
            {isStale ? "This is taking longer than expected" : isActivelyProcessing ? "Processing in background..." : "No lecture loaded"}
          </h2>
          <p className="text-sm mb-6" style={{ color: "var(--text-secondary)" }}>
            {isStale
              ? "The generation may have finished on another device, or something went wrong. You can try uploading again."
              : isActivelyProcessing
              ? "Your lecture is being generated. View the progress or wait here — it'll appear automatically when ready."
              : "Upload a lecture recording or transcript to get started."}
          </p>
          {isStale ? (
            <button
              onClick={() => router.push("/upload")}
              className="btn-glow px-6 py-3 rounded-xl text-sm font-semibold"
              style={{
                background: "linear-gradient(135deg, var(--accent), #FF8555)",
                color: "#fff",
                boxShadow: "0 8px 32px var(--accent-glow)",
              }}
            >
              Try again
            </button>
          ) : isActivelyProcessing ? (
            <div className="flex flex-col items-center justify-center gap-3">
              {/* Spinner */}
              <div
                className="w-6 h-6 rounded-full border-2 animate-spin"
                style={{
                  borderColor: "var(--border)",
                  borderTopColor: "var(--accent)",
                }}
              />
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                This page updates automatically — no need to refresh.
              </p>
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

  const sessionName = activeSession?.name || "Untitled Lecture";

  const activeSectionData = transcript[activeSection];
  const activeSectionSlides = activeSectionData
    ? (slideGroups[activeSectionData.slide_number] || [])
    : [];

  return (
    <div className="flex h-full overflow-hidden">
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

        {/* Download buttons */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => downloadSlidesPDF(slides, transcript, sessionName)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
            style={{ background: "var(--bg-elevated)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}
            onMouseEnter={(e) => { e.currentTarget.style.color = "var(--accent)"; e.currentTarget.style.borderColor = "var(--accent)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = "var(--text-secondary)"; e.currentTarget.style.borderColor = "var(--border)"; }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
            Slides PDF
          </button>
          <button
            onClick={() => downloadTranscriptPDF(transcript, sessionName)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
            style={{ background: "var(--bg-elevated)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}
            onMouseEnter={(e) => { e.currentTarget.style.color = "var(--accent)"; e.currentTarget.style.borderColor = "var(--accent)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = "var(--text-secondary)"; e.currentTarget.style.borderColor = "var(--border)"; }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14,2 14,8 20,8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>
            Notes PDF
          </button>
        </div>

        {/* Current section's slide(s) */}
        {activeSectionSlides.length > 0 ? (
          <SlideCardGroup key={activeSection} cards={activeSectionSlides} onImageClick={setLightboxSrc} />
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
        style={{ padding: "32px 24px 50vh 32px" }}
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
          className="md:hidden text-lg font-semibold mb-4 outline-none rounded-lg px-2 py-1 -ml-2 transition-colors"
          style={{ color: "var(--text-secondary)", cursor: "text" }}
          onMouseEnter={(e) => { e.currentTarget.style.background = "var(--bg-elevated)"; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
          onFocus={(e) => { e.currentTarget.style.background = "var(--bg-elevated)"; e.currentTarget.style.color = "var(--text-primary)"; }}
        >
          {sessionName}
        </h1>

        {/* Mobile download buttons */}
        <div className="md:hidden flex gap-2 mb-8">
          <button
            onClick={() => downloadSlidesPDF(slides, transcript, sessionName)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium"
            style={{ background: "var(--bg-elevated)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
            Slides PDF
          </button>
          <button
            onClick={() => downloadTranscriptPDF(transcript, sessionName)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium"
            style={{ background: "var(--bg-elevated)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14,2 14,8 20,8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>
            Notes PDF
          </button>
        </div>

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

        {/* Streaming indicator — still generating, more sections to come */}
        {hasStreamingContent && !store.markdown && (
          <div
            className="flex items-center gap-3 py-8 px-4 rounded-xl"
            style={{ background: "var(--bg-elevated)", color: "var(--text-muted)" }}
          >
            <div
              className="w-4 h-4 rounded-full border-2 border-t-transparent animate-spin shrink-0"
              style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}
            />
            <span className="text-sm">Writing more sections…</span>
          </div>
        )}
      </div>
    </div>
  );
}
