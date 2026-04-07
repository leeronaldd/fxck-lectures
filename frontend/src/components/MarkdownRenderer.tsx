"use client";

import { useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import rehypeSlug from "rehype-slug";
import type { Components } from "react-markdown";

interface MarkdownRendererProps {
  content: string;
}

function Lightbox({
  src,
  alt,
  onClose,
}: {
  src: string;
  alt: string;
  onClose: () => void;
}) {
  return (
    <div className="lightbox-overlay" onClick={onClose}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt={alt} />
    </div>
  );
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  const [lightboxSrc, setLightboxSrc] = useState<{
    src: string;
    alt: string;
  } | null>(null);

  const closeLightbox = useCallback(() => setLightboxSrc(null), []);

  // Process skip lines: lines starting with ⏭️
  const processedContent = content.replace(
    /^⏭️\s*\*\*(.+?)\s*\(CI%\s*(\d+)%?\)\*\*\s*—\s*(.+)$/gm,
    '<div class="skip-line"><span>⏭️</span><span class="ci-badge">CI $2%</span><span><strong>$1</strong> — Background context, low exam priority.</span></div>'
  );

  const components: Components = {
    // Fix image paths and add lightbox
    img: ({ src, alt, ...props }) => {
      const fixedSrc = src?.replace(
        /^screenshots\//,
        "/data/screenshots/"
      ) || "";
      return (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          {...props}
          src={fixedSrc}
          alt={alt || "Lecture slide"}
          onClick={() => setLightboxSrc({ src: fixedSrc, alt: alt || "" })}
          loading="lazy"
        />
      );
    },

    // Style heading 2s with section anchors
    h2: ({ children, id, ...props }) => (
      <h2 id={id} {...props}>
        {children}
      </h2>
    ),

    // Detect exam-relevant paragraphs
    p: ({ children, ...props }) => {
      const text =
        typeof children === "string"
          ? children
          : Array.isArray(children)
          ? children
              .map((c) => (typeof c === "string" ? c : ""))
              .join("")
          : "";

      const isExamAlert =
        /\b(exam|test question|for your exam|on the exam|if a test question)\b/i.test(
          text
        );

      if (isExamAlert) {
        return (
          <div className="exam-alert">
            <p {...props}>{children}</p>
          </div>
        );
      }

      return <p {...props}>{children}</p>;
    },
  };

  return (
    <>
      <div className="doc-content">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeRaw, rehypeSlug]}
          components={components}
        >
          {processedContent}
        </ReactMarkdown>
      </div>

      {lightboxSrc && (
        <Lightbox
          src={lightboxSrc.src}
          alt={lightboxSrc.alt}
          onClose={closeLightbox}
        />
      )}
    </>
  );
}
