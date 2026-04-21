"use client";

import { useState } from "react";
import type { LectureScore, LectureScoreLabel, TranscriptSection } from "@/lib/types";

interface Props {
  // Preferred source of truth — Flash's scoring from the completeness checker.
  // When present, the card shows LLM-judged scores, a personalised one-line
  // comment, and Flash's time-saved estimate. When absent (older sessions or
  // the completeness check was skipped), we fall back to a math-based
  // approximation so the card still renders something useful.
  lectureScore: LectureScore | null;
  transcript: TranscriptSection[];
  sessionName: string;
}

// ═══════════════════════════════════════════════════════════════════════════
// Label → colour mapping. Shared between the in-app card and the OG image.
// 5-tier scale: rough / ok / good / great / excellent.
// ═══════════════════════════════════════════════════════════════════════════

const LABEL_COLORS: Record<LectureScoreLabel, string> = {
  rough: "#ef4444",      // red
  ok: "#f97316",         // orange
  good: "#eab308",       // yellow
  great: "#84cc16",      // lime
  excellent: "#22c55e",  // green
};

function labelForScore(overall: number): LectureScoreLabel {
  if (overall < 20) return "rough";
  if (overall < 40) return "ok";
  if (overall < 60) return "good";
  if (overall < 80) return "great";
  return "excellent";
}

function barColor(value: number): string {
  if (value < 30) return "#ef4444";
  if (value < 50) return "#f97316";
  if (value < 70) return "#eab308";
  if (value < 85) return "#84cc16";
  return "#22c55e";
}

// ═══════════════════════════════════════════════════════════════════════════
// Fallback scorer — used only when Flash's lectureScore is missing.
// Produces plausible numbers from the generated document's properties so the
// card never renders empty. Not meant to be accurate; accurate scoring lives
// in the completeness checker now.
// ═══════════════════════════════════════════════════════════════════════════

function fallbackScore(
  transcript: TranscriptSection[],
  sessionName: string
): LectureScore | null {
  if (!transcript.length) return null;

  const avgEI =
    transcript.reduce((s, t) => s + (t.ei_percent ?? 50), 0) / transcript.length;
  const variance =
    transcript.reduce((s, t) => s + Math.pow((t.ei_percent ?? 50) - avgEI, 2), 0) /
    transcript.length;

  const clarity = Math.round(Math.max(20, Math.min(70, 60 - variance * 0.25)));
  const focus = Math.round(Math.max(20, Math.min(70, 70 - transcript.length * 1.8)));
  const avgLen =
    transcript.reduce((s, t) => s + (t.narrative?.length ?? 0), 0) / transcript.length;
  const efficiency = Math.round(Math.max(20, Math.min(70, 60 - avgLen / 140)));
  const overall = Math.round((clarity + focus + efficiency) / 3);

  const totalWords = transcript.reduce(
    (s, t) => s + (t.narrative?.split(" ").length ?? 0),
    0
  );
  const readMinutes = Math.round(totalWords / 200);
  const timeSaved = Math.max(5, Math.round(readMinutes * 3.5) - readMinutes);

  void sessionName; // kept in signature for future use

  return {
    overall,
    clarity,
    focus,
    efficiency,
    label: labelForScore(overall),
    comment: "Score based on document structure — Flash couldn't review this run.",
    time_saved_min: timeSaved,
  };
}

// ═══════════════════════════════════════════════════════════════════════════
// Small bar
// ═══════════════════════════════════════════════════════════════════════════

function ScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs w-24 shrink-0" style={{ color: "var(--text-muted)" }}>
        {label}
      </span>
      <div
        className="flex-1 rounded-full overflow-hidden"
        style={{ height: 6, background: "var(--bg-elevated)" }}
      >
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${value}%`, background: barColor(value) }}
        />
      </div>
      <span
        className="text-xs w-8 text-right shrink-0 font-mono"
        style={{ color: "var(--text-secondary)" }}
      >
        {value}%
      </span>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Card
// ═══════════════════════════════════════════════════════════════════════════

export default function LectureScoreCard({
  lectureScore,
  transcript,
  sessionName,
}: Props) {
  const [copied, setCopied] = useState(false);
  const score = lectureScore ?? fallbackScore(transcript, sessionName);
  if (!score) return null;

  const { overall, clarity, focus, efficiency, label, comment, time_saved_min } =
    score;
  const overallColor = LABEL_COLORS[label];

  const ogParams = new URLSearchParams({
    overall: String(overall),
    clarity: String(clarity),
    focus: String(focus),
    efficiency: String(efficiency),
    label,
    comment,
    time_saved: String(time_saved_min),
    name: sessionName,
  });
  const ogUrl = `/api/og/lecture-score?${ogParams.toString()}`;

  const handleShare = async () => {
    const text = `My lecture scored ${overall}/100 on Klare (${label})\n\n"${comment}"\n\nklareai.com`;
    const absoluteOgUrl =
      typeof window !== "undefined" ? `${window.location.origin}${ogUrl}` : ogUrl;
    try {
      if (typeof navigator !== "undefined" && navigator.share) {
        try {
          const res = await fetch(absoluteOgUrl);
          const blob = await res.blob();
          const file = new File([blob], "klare-lecture-score.png", {
            type: "image/png",
          });
          if (navigator.canShare && navigator.canShare({ files: [file] })) {
            await navigator.share({ text, files: [file] });
            return;
          }
          await navigator.share({ text, url: absoluteOgUrl });
          return;
        } catch {
          // fall through
        }
      }
      await navigator.clipboard.writeText(`${text}\n${absoluteOgUrl}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // cancelled
    }
  };

  const handleDownload = () => {
    window.open(ogUrl, "_blank");
  };

  return (
    <div
      className="rounded-2xl p-6 mt-2"
      style={{
        background:
          "linear-gradient(135deg, rgba(239,68,68,0.04), rgba(255,107,53,0.07))",
        border: "1px solid rgba(239,68,68,0.16)",
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-5">
        <div>
          <p
            className="text-xs font-medium mb-0.5"
            style={{ color: "var(--text-muted)" }}
          >
            Lecture Score
          </p>
          <p
            className="text-xs"
            style={{ color: "var(--text-muted)", opacity: 0.7 }}
          >
            {sessionName}
          </p>
        </div>
        <div className="text-right">
          <span
            className="text-4xl font-bold tracking-tight"
            style={{ color: overallColor }}
          >
            {overall}
          </span>
          <span
            className="text-lg font-medium"
            style={{ color: "var(--text-muted)" }}
          >
            /100
          </span>
          <p
            className="text-xs mt-0.5 capitalize"
            style={{ color: overallColor }}
          >
            {label}
          </p>
        </div>
      </div>

      {/* Dimension bars */}
      <div className="space-y-3 mb-5">
        <ScoreBar label="Clarity" value={clarity} />
        <ScoreBar label="Focus" value={focus} />
        <ScoreBar label="Efficiency" value={efficiency} />
      </div>

      {/* Comment line */}
      <p
        className="text-sm italic mb-4 px-3 py-2.5 rounded-xl leading-relaxed"
        style={{
          color: "var(--text-secondary)",
          background: "rgba(0,0,0,0.2)",
          borderLeft: `3px solid ${overallColor}80`,
        }}
      >
        &ldquo;{comment}&rdquo;
      </p>

      {/* Time stat + actions */}
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          Klare saved you ~{time_saved_min} min
        </p>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={handleDownload}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium transition-all"
            style={{
              background: "transparent",
              color: "var(--text-secondary)",
              border: "1px solid var(--border)",
            }}
            title="Preview image to save or post"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <polyline points="21 15 16 10 5 21" />
            </svg>
            Preview
          </button>
          <button
            onClick={handleShare}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all"
            style={{
              background: copied ? "rgba(34,197,94,0.15)" : `${overallColor}22`,
              color: copied ? "#22c55e" : overallColor,
              border: `1px solid ${copied ? "rgba(34,197,94,0.3)" : `${overallColor}50`}`,
            }}
          >
            {copied ? (
              <>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                Copied
              </>
            ) : (
              <>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" />
                  <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" /><line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
                </svg>
                Share
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
