"use client";

import { useEffect, useState } from "react";

interface SlideEntry {
  index: number;
  filename: string;
  timestamp_seconds: number;
  timestamp_display: string;
  detection_diff: number;
}

/**
 * Dev gallery for reviewing the tuned-slide-extraction output.
 * Reads /extraction-test/manifest.json (produced by test_slide_extraction.py)
 * and shows every extracted slide in a scrollable grid so the user can eyeball
 * whether any lecture slides are still missing.
 */
export default function ExtractionTestPage() {
  const [slides, setSlides] = useState<SlideEntry[] | null>(null);
  const [lightbox, setLightbox] = useState<string | null>(null);

  useEffect(() => {
    fetch("/extraction-test/manifest.json")
      .then((r) => r.json())
      .then(setSlides)
      .catch(() => setSlides([]));
  }, []);

  if (slides === null) {
    return (
      <div className="p-8 text-sm" style={{ color: "var(--text-muted)" }}>
        Loading manifest…
      </div>
    );
  }

  if (!slides.length) {
    return (
      <div className="p-8 text-sm" style={{ color: "var(--text-muted)" }}>
        No manifest found. Run <code>python test_slide_extraction.py</code> to
        generate one.
      </div>
    );
  }

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      {lightbox && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center cursor-zoom-out"
          style={{ background: "rgba(0,0,0,0.92)" }}
          onClick={() => setLightbox(null)}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={lightbox}
            alt="Slide"
            style={{ maxWidth: "95vw", maxHeight: "95vh", borderRadius: 8 }}
          />
        </div>
      )}

      <div className="mb-6">
        <h1
          className="text-2xl font-bold mb-1"
          style={{ color: "var(--text-primary)" }}
        >
          Slide extraction test — {slides.length} slides
        </h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Tuned params: threshold 15, 2 fps sampling, perceptual-hash dedup.
          Click any slide to expand. Flag missing slides and report back.
        </p>
      </div>

      <div
        className="grid gap-3"
        style={{
          gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
        }}
      >
        {slides.map((s) => {
          const src = `/extraction-test/${s.filename}`;
          return (
            <div
              key={s.index}
              className="rounded-lg overflow-hidden border"
              style={{
                background: "var(--bg-surface)",
                borderColor: "var(--border)",
              }}
            >
              <button
                onClick={() => setLightbox(src)}
                className="w-full cursor-zoom-in"
                style={{ background: "white" }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={src}
                  alt={`Slide ${s.index}`}
                  style={{
                    width: "100%",
                    height: 160,
                    objectFit: "contain",
                    display: "block",
                  }}
                  loading="lazy"
                />
              </button>
              <div
                className="px-3 py-2 text-xs flex justify-between"
                style={{ color: "var(--text-muted)" }}
              >
                <span>
                  #{s.index} · {s.timestamp_display}
                </span>
                <span>Δ{s.detection_diff}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
