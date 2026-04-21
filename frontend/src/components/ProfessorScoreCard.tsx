"use client";

import { useState } from "react";
import type { TranscriptSection } from "@/lib/types";

interface Props {
  transcript: TranscriptSection[];
  sessionName: string;
}

function computeScores(transcript: TranscriptSection[]) {
  if (!transcript.length) return null;

  // Clarity: how well EI% is distributed — low average EI means prof spent time
  // on unimportant things, high variance means unpredictable delivery
  const avgEI = transcript.reduce((s, t) => s + (t.ei_percent ?? 50), 0) / transcript.length;
  const eiValues = transcript.map((t) => t.ei_percent ?? 50);
  const variance =
    eiValues.reduce((s, v) => s + Math.pow(v - avgEI, 2), 0) / eiValues.length;

  // Sections count: more fragmented = harder to follow
  const sectionCount = transcript.length;

  // Average narrative length: very long = Klare had to fill in a lot
  const avgLen =
    transcript.reduce((s, t) => s + (t.narrative?.length ?? 0), 0) / transcript.length;

  // Score each dimension (all kept intentionally low — these are bad professors)
  const clarity = Math.round(Math.max(10, Math.min(62, 58 - variance * 0.3)));
  const focus = Math.round(Math.max(12, Math.min(65, 70 - sectionCount * 2.2)));
  const efficiency = Math.round(
    Math.max(8, Math.min(58, 55 - (avgLen / 120)))
  );
  const overall = Math.round((clarity + focus + efficiency) / 3);

  // Roast line — pick based on which dimension scored lowest
  const minDim = Math.min(clarity, focus, efficiency);
  const roasts: Record<string, string> = {
    clarity:
      "Gave 3 definitions before explaining what the thing actually does.",
    focus: "Spent 20 minutes on background no one asked for.",
    efficiency: "Somehow made this topic sound harder than it is.",
  };
  const lowestLabel =
    clarity === minDim ? "clarity" : focus === minDim ? "focus" : "efficiency";
  const roastLine = roasts[lowestLabel];

  // Approximate time saved: rough heuristic from narrative word count
  const totalWords = transcript.reduce(
    (s, t) => s + (t.narrative?.split(" ").length ?? 0),
    0
  );
  const readMinutes = Math.round(totalWords / 200); // ~200wpm reading speed
  // Assume original lecture was ~3-4x longer to deliver
  const lectureMinutes = Math.round(readMinutes * 3.5);
  const saved = Math.max(5, lectureMinutes - readMinutes);

  return { clarity, focus, efficiency, overall, roastLine, readMinutes, saved };
}

function ScoreBar({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  return (
    <div className="flex items-center gap-3">
      <span
        className="text-xs w-24 shrink-0"
        style={{ color: "var(--text-muted)" }}
      >
        {label}
      </span>
      <div
        className="flex-1 rounded-full overflow-hidden"
        style={{ height: 6, background: "var(--bg-elevated)" }}
      >
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${value}%`,
            background:
              value < 30
                ? "#ef4444"
                : value < 50
                ? "#f97316"
                : "#22c55e",
          }}
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

export default function ProfessorScoreCard({ transcript, sessionName }: Props) {
  const [copied, setCopied] = useState(false);
  const scores = computeScores(transcript);
  if (!scores) return null;

  const { clarity, focus, efficiency, overall, roastLine, readMinutes, saved } =
    scores;

  const label =
    overall < 25 ? "Train wreck" : overall < 40 ? "Rough" : overall < 55 ? "Needs work" : "Passable";

  const handleShare = async () => {
    const text = `My professor scored ${overall}/100 on the Klare clarity test\n\nClarity: ${clarity}%  Focus: ${focus}%  Efficiency: ${efficiency}%\n\n"${roastLine}"\n\nklareai.com`;
    try {
      if (navigator.share) {
        await navigator.share({ text });
      } else {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    } catch {
      // user cancelled share
    }
  };

  return (
    <div
      className="rounded-2xl p-6 mt-2"
      style={{
        background:
          "linear-gradient(135deg, rgba(239,68,68,0.06), rgba(255,107,53,0.08))",
        border: "1px solid rgba(239,68,68,0.18)",
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-5">
        <div>
          <p className="text-xs font-medium mb-0.5" style={{ color: "var(--text-muted)" }}>
            Professor Clarity Score
          </p>
          <p className="text-xs" style={{ color: "var(--text-muted)", opacity: 0.7 }}>
            {sessionName}
          </p>
        </div>
        <div className="text-right">
          <span
            className="text-4xl font-bold tracking-tight"
            style={{ color: overall < 40 ? "#ef4444" : "#f97316" }}
          >
            {overall}
          </span>
          <span className="text-lg font-medium" style={{ color: "var(--text-muted)" }}>
            /100
          </span>
          <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
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

      {/* Roast line */}
      <p
        className="text-sm italic mb-4 px-3 py-2.5 rounded-xl leading-relaxed"
        style={{
          color: "var(--text-secondary)",
          background: "rgba(0,0,0,0.2)",
          borderLeft: "3px solid rgba(239,68,68,0.5)",
        }}
      >
        &ldquo;{roastLine}&rdquo;
      </p>

      {/* Time stat + share */}
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          Klare saved you ~{saved} min
        </p>
        <button
          onClick={handleShare}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all shrink-0"
          style={{
            background: copied ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.12)",
            color: copied ? "#22c55e" : "#ef4444",
            border: `1px solid ${copied ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)"}`,
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
              Share my professor&apos;s score
            </>
          )}
        </button>
      </div>
    </div>
  );
}
