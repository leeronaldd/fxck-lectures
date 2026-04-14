"use client";

import React, { useState } from "react";
import type { SlideCard } from "@/lib/types";

/** Render inline markdown (bold, italic) to HTML */
function inlineMarkdown(text: string): string {
  return text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/\*\*([\s\S]+?)\*\*/g, '<strong style="color: var(--accent)">$1</strong>')
    .replace(/(?<!\*)\*(?!\*)([\s\S]+?)(?<!\*)\*(?!\*)/g, "<em>$1</em>");
}

function SlideImage({ src, alt, onClick }: { src: string; alt: string; onClick: () => void }) {
  const [status, setStatus] = useState<"loading" | "loaded" | "error">("loading");
  const imgRef = React.useRef<HTMLImageElement>(null);

  // Handle case where image loads before React hydration attaches onLoad
  React.useEffect(() => {
    if (imgRef.current?.complete && imgRef.current.naturalWidth > 0) {
      setStatus("loaded");
    }
  }, [src]);

  if (status === "error") {
    return (
      <div className="px-3 pb-3">
        <div className="w-full rounded-xl flex flex-col items-center justify-center py-8 gap-2"
          style={{ background: "var(--bg-elevated)", border: "1px dashed var(--border)" }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--text-muted)" }}>
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
            <circle cx="8.5" cy="8.5" r="1.5"/>
            <polyline points="21,15 16,10 5,21"/>
          </svg>
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>Slide image unavailable</span>
        </div>
      </div>
    );
  }

  return (
    <div className="px-3 pb-3">
      <button
        onClick={onClick}
        className="w-full rounded-xl overflow-hidden bg-white cursor-zoom-in hover:ring-2 hover:ring-[var(--accent)] transition-all relative"
      >
        {status === "loading" && (
          <div className="absolute inset-0 flex items-center justify-center" style={{ background: "var(--bg-elevated)" }}>
            <div className="w-5 h-5 border-2 border-t-transparent rounded-full animate-spin"
              style={{ borderColor: "var(--text-muted)", borderTopColor: "transparent" }} />
          </div>
        )}
        <img
          ref={imgRef}
          src={src}
          alt={alt}
          className="w-full transition-opacity duration-200"
          style={{ opacity: status === "loaded" ? 1 : 0, maxHeight: "280px", objectFit: "contain" }}
          loading="lazy"
          onLoad={() => setStatus("loaded")}
          onError={() => setStatus("error")}
        />
      </button>
    </div>
  );
}

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

/** Resolve a slide image_ref to a full URL.
 *  "screenshots/screenshot_005.jpg" → "{API_URL}/api/screenshots/screenshot_005.jpg"
 */
function resolveImageUrl(imageRef: string): string {
  if (imageRef.startsWith("http")) return imageRef;
  if (imageRef.startsWith("/")) return imageRef;
  if (imageRef.startsWith("screenshots/")) {
    const filename = imageRef.replace("screenshots/", "");
    return `${API_URL}/api/screenshots/${filename}`;
  }
  return `/${imageRef}`;
}

export function SlideCardComponent({
  card,
  onImageClick,
}: {
  card: SlideCard;
  onImageClick?: (src: string) => void;
}) {
  if (!card) return null;
  const isProfSlide = card.card_type === "professor_slide";

  return (
    <div
      className="rounded-2xl overflow-hidden border"
      style={{
        background: "var(--bg-surface)",
        borderColor: "var(--border)",
      }}
    >
      {/* Card header */}
      <div
        className="px-4 py-3 flex items-center justify-between border-b"
        style={{ borderColor: "var(--border)" }}
      >
        <div className="flex items-center gap-2">
          <span
            className="text-xs font-mono font-bold px-2 py-0.5 rounded-md"
            style={{
              background: "var(--accent-dim)",
              color: "var(--accent)",
            }}
          >
            {card.slide_id}
          </span>
          <span
            className="text-sm font-semibold"
            style={{ color: "var(--text-primary)" }}
          >
            {card.title}
          </span>
        </div>
        <span
          className="text-xs px-2 py-0.5 rounded-full"
          style={{
            background:
              card.ei_percent >= 70
                ? "rgba(255, 176, 32, 0.15)"
                : "rgba(255,255,255,0.06)",
            color:
              card.ei_percent >= 70 ? "var(--ci-high)" : "var(--text-muted)",
          }}
        >
          EI {card.ei_percent}%
        </span>
      </div>

      {/* Bullet points (diagram cards only) */}
      {!isProfSlide && card.bullet_points.length > 0 && (
        <div className="px-4 py-3 space-y-1.5">
          {card.bullet_points.map((bp, i) => (
            <div key={i} className="flex items-start gap-2 text-sm">
              <span style={{ color: "var(--accent)" }} className="mt-0.5 shrink-0">
                {"\u2022"}
              </span>
              <span style={{ color: "var(--text-primary)" }} dangerouslySetInnerHTML={{ __html: inlineMarkdown(bp) }} />
            </div>
          ))}
        </div>
      )}

      {/* Image — clickable to expand */}
      {card.image_ref && !card.image_ref.startsWith("[") && (
        <SlideImage
          src={resolveImageUrl(card.image_ref)}
          alt={card.title}
          onClick={() => onImageClick?.(resolveImageUrl(card.image_ref))}
        />
      )}

      {/* Diagram suggestion (no image available) */}
      {card.image_ref && card.image_ref.startsWith("[") && (
        <div className="px-4 py-3 text-xs italic" style={{ color: "var(--text-muted)" }}>
          {card.image_ref}
        </div>
      )}

      {/* Exam tip */}
      {card.exam_tip && (
        <div
          className="px-4 py-3 text-xs border-t"
          style={{
            borderColor: "var(--border)",
            background: "var(--exam-bg)",
            color: "var(--ci-high)",
          }}
        >
          <span className="font-semibold">Exam tip:</span>{" "}
          <span dangerouslySetInnerHTML={{ __html: inlineMarkdown(card.exam_tip) }} />
        </div>
      )}
    </div>
  );
}

export function SlideCardGroup({
  cards,
  onImageClick,
}: {
  cards: SlideCard[];
  onImageClick?: (src: string) => void;
}) {
  const [activeIdx, setActiveIdx] = useState(0);
  const safeIdx = Math.min(activeIdx, cards.length - 1);

  if (cards.length === 1) {
    return <SlideCardComponent card={cards[0]} onImageClick={onImageClick} />;
  }

  return (
    <div className="space-y-2">
      <SlideCardComponent card={cards[safeIdx]} onImageClick={onImageClick} />
      {/* Dot indicators */}
      <div className="flex items-center justify-center gap-2 py-1">
        {cards.map((card, i) => (
          <button
            key={card.slide_id}
            onClick={() => setActiveIdx(i)}
            className="flex items-center gap-1 px-2 py-1 rounded-full text-xs transition-all"
            style={{
              background: i === activeIdx ? "var(--accent-dim)" : "transparent",
              color: i === activeIdx ? "var(--accent)" : "var(--text-muted)",
              border: `1px solid ${i === activeIdx ? "var(--accent)" : "var(--border)"}`,
            }}
          >
            {card.slide_id}
          </button>
        ))}
      </div>
    </div>
  );
}
