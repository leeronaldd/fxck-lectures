"use client";

import type { TranscriptSection } from "@/lib/types";

export default function NarrativeSection({ section }: { section: TranscriptSection }) {
  function renderMarkdown(text: string) {
    return text.split("\n\n").map((para, i) => {
      const isStruck = para.startsWith("~~") && para.endsWith("~~");
      const cleanPara = isStruck ? para.slice(2, -2) : para;

      // Process inline markdown
      const html = cleanPara
        .replace(/\*\*(.+?)\*\*/g, '<strong style="color: var(--accent)">$1</strong>')
        .replace(/\*(.+?)\*/g, "<em>$1</em>")
        .replace(/~~(.+?)~~/g, '<del style="opacity: 0.4">$1</del>');

      return (
        <p
          key={i}
          className="mb-4 leading-relaxed text-[15px]"
          style={{
            color: isStruck ? "var(--text-muted)" : "var(--text-primary)",
            textDecoration: isStruck ? "line-through" : "none",
            opacity: isStruck ? 0.5 : 1,
          }}
          dangerouslySetInnerHTML={{ __html: isStruck ? `<del>${html}</del>` : html }}
        />
      );
    });
  }

  return (
    <div>
      <h2
        className="text-xl font-bold mb-6"
        style={{ color: "var(--text-primary)" }}
      >
        {section.title}
      </h2>
      {renderMarkdown(section.narrative)}
    </div>
  );
}
