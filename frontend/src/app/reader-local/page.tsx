"use client";

import { useEffect, useRef, useState } from "react";
import { SlideCardGroup } from "@/components/SlideCard";
import NarrativeSection from "@/components/NarrativeSection";
import ImageLightbox from "@/components/ImageLightbox";
import type { SlideCard, TranscriptSection } from "@/lib/types";

interface PreviewDoc {
  name?: string;
  slides: SlideCard[];
  transcript: TranscriptSection[];
}

/**
 * Local-only preview of a generated document. Reads /chem_preview.json
 * from the public folder and renders it with the same layout as /reader,
 * bypassing Supabase sessions and the pipeline backend. Pure dev tool —
 * not linked from the app, not meant for production.
 */
export default function ReaderLocalPage() {
  const [doc, setDoc] = useState<PreviewDoc | null>(null);
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState(0);
  const sectionRefs = useRef<(HTMLDivElement | null)[]>([]);
  const rightPanelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    fetch("/chem_preview.json")
      .then((r) => r.json())
      .then(setDoc)
      .catch((e) => console.error("Failed to load preview:", e));
  }, []);

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

  if (!doc) {
    return (
      <div className="flex-1 flex items-center justify-center py-24">
        <div className="text-sm" style={{ color: "var(--text-muted)" }}>
          Loading preview…
        </div>
      </div>
    );
  }

  const { slides, transcript } = doc;
  const sessionName = doc.name || "Local preview";

  const slideGroups: Record<number, SlideCard[]> = {};
  for (const card of slides) {
    const num = parseInt(card.slide_id.replace(/[a-z]/g, ""));
    if (!slideGroups[num]) slideGroups[num] = [];
    slideGroups[num].push(card);
  }

  const activeSectionData = transcript[activeSection];
  const activeSectionSlides = activeSectionData
    ? slideGroups[activeSectionData.slide_number] || []
    : [];

  return (
    <div className="flex h-full overflow-hidden">
      {lightboxSrc && (
        <ImageLightbox src={lightboxSrc} onClose={() => setLightboxSrc(null)} />
      )}

      <div
        className="hidden md:flex flex-col shrink-0 overflow-y-auto"
        style={{
          width: "44%",
          padding: "32px 20px 64px 24px",
          borderRight: "1px solid var(--border)",
        }}
      >
        <h1
          className="text-lg font-semibold mb-6"
          style={{ color: "var(--text-secondary)" }}
        >
          {sessionName}
        </h1>

        {activeSectionSlides.length > 0 ? (
          <SlideCardGroup
            key={activeSection}
            cards={activeSectionSlides}
            onImageClick={setLightboxSrc}
          />
        ) : (
          <div
            className="rounded-2xl p-8 text-center border"
            style={{
              background: "var(--bg-surface)",
              borderColor: "var(--border)",
            }}
          >
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              No slides for this section
            </p>
          </div>
        )}

        {transcript.length > 1 && (
          <p
            className="mt-4 text-xs"
            style={{ color: "var(--text-muted)" }}
          >
            Section {activeSection + 1} / {transcript.length}
          </p>
        )}
      </div>

      <div
        ref={rightPanelRef}
        className="flex-1 min-w-0 overflow-y-auto"
        style={{ padding: "32px 24px 50vh 32px" }}
        onScroll={handleScroll}
      >
        <h1
          className="md:hidden text-lg font-semibold mb-4"
          style={{ color: "var(--text-secondary)" }}
        >
          {sessionName}
        </h1>

        {transcript.map((section, i) => (
          <div
            key={i}
            ref={(el) => {
              sectionRefs.current[i] = el;
            }}
            className="mb-12"
          >
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
              <hr
                className="mt-12"
                style={{ borderColor: "var(--border)" }}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
