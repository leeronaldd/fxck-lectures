"use client";

import { useState } from "react";
import type { SlideCard } from "@/lib/types";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

/** Resolve a slide image_ref to a full URL.
 *  "screenshots/screenshot_005.jpg" → "{API_URL}/api/screenshots/screenshot_005.jpg"
 */
function resolveImageUrl(imageRef: string): string {
  if (imageRef.startsWith("http")) return imageRef;
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
              <span style={{ color: "var(--text-primary)" }}>{bp}</span>
            </div>
          ))}
        </div>
      )}

      {/* Image — clickable to expand */}
      {card.image_ref && !card.image_ref.startsWith("[") && (
        <div className="px-3 pb-3">
          <button
            onClick={() => onImageClick?.(resolveImageUrl(card.image_ref))}
            className="w-full rounded-xl overflow-hidden bg-white cursor-zoom-in hover:ring-2 hover:ring-[var(--accent)] transition-all"
          >
            <img
              src={resolveImageUrl(card.image_ref)}
              alt={card.title}
              className="w-full h-auto"
            />
          </button>
        </div>
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
          <span className="font-semibold">Exam tip:</span> {card.exam_tip}
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

  if (cards.length === 1) {
    return <SlideCardComponent card={cards[0]} onImageClick={onImageClick} />;
  }

  return (
    <div className="space-y-2">
      <SlideCardComponent card={cards[activeIdx]} onImageClick={onImageClick} />
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
