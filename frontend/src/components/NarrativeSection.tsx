"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeRaw from "rehype-raw";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import type { TranscriptSection } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

/**
 * Defensive rewrite for inline markdown image refs.
 *
 * In production the backend pipeline.py rewrites `screenshots/xxx.png`
 * → GCS URL before the transcript reaches the frontend. This handler
 * is the safety net for any URL the backend regex misses (unusual
 * filename, cached session from an older backend build, local preview
 * pages that skip the pipeline).
 *
 *   - absolute URLs (http://, https://, gs://) pass through unchanged
 *   - paths that already start with `/` pass through (local preview
 *     uses `/preview-screenshots/...`)
 *   - `screenshots/xxx.png` falls through to the `/api/screenshots/`
 *     endpoint that SlideCard also uses
 */
function resolveImgSrc(raw: string): string {
  if (!raw) return "";
  if (/^(https?:|gs:|data:)/i.test(raw)) return raw;
  if (raw.startsWith("/")) return raw;
  if (raw.startsWith("screenshots/")) {
    const filename = raw.replace("screenshots/", "");
    return API_URL
      ? `${API_URL}/api/screenshots/${filename}`
      : `/preview-screenshots/${filename}`;
  }
  return raw;
}

/**
 * Strip a leading markdown image from the narrative.
 *
 * The writer (both single-writer and multi-agent V3) emits every section
 * with the slide image at the top — `![title](screenshots/xxx.png)\n\n...`.
 * That was originally for markdown-only previews, but in the two-panel
 * reader the SlideCard component already displays the image (left pane
 * on desktop, stacked above the narrative on mobile). Rendering the
 * inline image here shows it twice.
 *
 * Strip only the *first* leading image so images mid-narrative (rare but
 * possible — an OpenStax figure referenced inline) still render.
 */
function stripLeadingImage(md: string): string {
  return md.replace(/^\s*!\[[^\]]*\]\([^)]*\)\s*\n+/, "");
}

/**
 * Renders a transcript section's narrative as markdown with KaTeX math.
 *
 * Previously this had its own inline regex-based renderer, which ignored
 * `$...$` math entirely — so `$1s^2$`, `$p_x$`, `$c = \lambda\nu$` showed
 * up as literal ASCII. We now route through react-markdown with
 * remark-math + rehype-katex so math renders properly. Custom styling
 * (accent-colored bold, inline image layout) is preserved via `components`.
 */
export default function NarrativeSection({
  section,
}: {
  section: TranscriptSection;
}) {
  return (
    <div>
      <h2
        className="text-xl font-bold mb-6"
        style={{ color: "var(--text-primary)" }}
      >
        {section.title}
      </h2>
      <div
        className="leading-relaxed text-[15px]"
        style={{ color: "var(--text-primary)" }}
      >
        <ReactMarkdown
          remarkPlugins={[remarkGfm, remarkMath]}
          rehypePlugins={[rehypeRaw, rehypeKatex]}
          components={{
            p: ({ children, ...props }) => (
              <p className="mb-4" {...props}>
                {children}
              </p>
            ),
            strong: ({ children }) => (
              <strong style={{ color: "var(--accent)" }}>{children}</strong>
            ),
            del: ({ children }) => (
              <del style={{ opacity: 0.4 }}>{children}</del>
            ),
            img: ({ src, alt }) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={resolveImgSrc(typeof src === "string" ? src : "")}
                alt={alt || ""}
                style={{
                  maxWidth: "100%",
                  borderRadius: "12px",
                  margin: "8px 0",
                }}
                loading="lazy"
              />
            ),
          }}
        >
          {stripLeadingImage(section.narrative)}
        </ReactMarkdown>
      </div>
    </div>
  );
}
