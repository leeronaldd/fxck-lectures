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
      <div className="flex items-center justify-center min-h-[80vh]">
        <div className="flex flex-col items-center gap-4">
          <div
            className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin"
            style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}
          />
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
            Loading lecture...
          </p>
        </div>
      </div>
    );
  }

  // Empty state
  if (!store.markdown) {
    return (
      <div className="flex-1 flex items-center justify-center px-4 py-24">
        <div className="text-center max-w-md">
          <div
            className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6"
            style={{ background: "var(--accent-dim)", color: "var(--accent)" }}
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
              <polyline points="14,2 14,8 20,8" />
            </svg>
          </div>
          <h2 className="text-xl font-bold mb-2" style={{ color: "var(--text-primary)" }}>
            No lecture loaded
          </h2>
          <p className="text-sm mb-6" style={{ color: "var(--text-secondary)" }}>
            Upload a lecture recording or transcript to get started.
          </p>
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

  return (
    <div className="flex flex-1 overflow-x-hidden">
      {/* Lightbox */}
      {lightboxSrc && (
        <ImageLightbox src={lightboxSrc} onClose={() => setLightboxSrc(null)} />
      )}

      <div className="flex-1 min-w-0 overflow-y-auto">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-8 pb-16">
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
