"use client";

import { useState } from "react";

interface Props {
  sessionId: string;
  sessionName: string;
}

/**
 * 1-click share button for a generated Klare document.
 *
 * Produces a public link at klareai.com/s/{sessionId} that anyone (no signin)
 * can open. This is the viral-loop hook: students share their re-taught doc
 * with classmates, each opened link surfaces the Klare footer, classmates
 * convert.
 *
 * On mobile: triggers the native share sheet (title + url) so the student can
 * blast it into a group chat / Instagram story with one tap.
 * On desktop: copies the link to clipboard with a 2s "Copied!" confirmation.
 */
export default function ShareButton({ sessionId, sessionName }: Props) {
  const [copied, setCopied] = useState(false);

  const handleShare = async () => {
    const url =
      typeof window !== "undefined"
        ? `${window.location.origin}/s/${sessionId}`
        : `/s/${sessionId}`;
    const shareText = `Here's my ${sessionName} notes — re-taught by Klare in 20 min instead of the 2hr lecture.`;

    try {
      if (typeof navigator !== "undefined" && navigator.share) {
        await navigator.share({
          title: sessionName,
          text: shareText,
          url,
        });
        return;
      }
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // User cancelled share — no-op
    }
  };

  return (
    <button
      onClick={handleShare}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
      style={{
        background: copied ? "rgba(34,197,94,0.12)" : "var(--accent-dim)",
        color: copied ? "#22c55e" : "var(--accent)",
        border: `1px solid ${copied ? "rgba(34,197,94,0.3)" : "rgba(255, 107, 53, 0.3)"}`,
      }}
      title={copied ? "Link copied!" : "Share a public read-only link with classmates"}
    >
      {copied ? (
        <>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          Link copied
        </>
      ) : (
        <>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="18" cy="5" r="3" />
            <circle cx="6" cy="12" r="3" />
            <circle cx="18" cy="19" r="3" />
            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
          </svg>
          Share with classmates
        </>
      )}
    </button>
  );
}
