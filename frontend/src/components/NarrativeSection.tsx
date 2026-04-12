"use client";

import type { TranscriptSection } from "@/lib/types";

export default function NarrativeSection({ section }: { section: TranscriptSection }) {
  function escapeHtml(str: string): string {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function renderMarkdown(text: string) {
    return text.split("\n\n").map((para, i) => {
      const isStruck = para.startsWith("~~") && para.endsWith("~~");
      const cleanPara = isStruck ? para.slice(2, -2) : para;

      // Escape HTML first to prevent XSS, then apply markdown formatting
      // Use [\s\S] instead of . to match across line breaks within a paragraph
      const html = escapeHtml(cleanPara)
        .replace(/\*\*([\s\S]+?)\*\*/g, '<strong style="color: var(--accent)">$1</strong>')
        .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "<em>$1</em>")
        .replace(/~~([\s\S]+?)~~/g, '<del style="opacity: 0.4">$1</del>');

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
