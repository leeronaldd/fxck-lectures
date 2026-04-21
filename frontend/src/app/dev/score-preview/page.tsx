"use client";

// Dev-only preview of LectureScoreCard without needing to sign in or run
// a real pipeline. Open http://localhost:PORT/dev/score-preview to see the
// card with mock data. Use the tier buttons to swap between label colours.

import { useState } from "react";
import LectureScoreCard from "@/components/LectureScoreCard";
import type { LectureScore, LectureScoreLabel, TranscriptSection } from "@/lib/types";

// Minimal mock transcript — only used by the fallback scorer if Flash's
// lecture_score is null. When we pass a real lectureScore below, this is
// largely ignored.
const mockTranscript: TranscriptSection[] = [
  {
    slide_number: 1,
    title: "Intro",
    narrative: "Placeholder narrative. ".repeat(40),
    ei_percent: 70,
    ei_reasoning: "",
  },
];

const MOCKS: Record<LectureScoreLabel, LectureScore> = {
  rough: {
    overall: 16,
    clarity: 12,
    focus: 18,
    efficiency: 18,
    label: "rough",
    comment: "Read definitions off the slide, no examples, one student laughed out of confusion.",
    time_saved_min: 92,
  },
  ok: {
    overall: 31,
    clarity: 24,
    focus: 35,
    efficiency: 34,
    label: "ok",
    comment: "Spent 12 minutes on the history of penicillin before touching peptidoglycan structure.",
    time_saved_min: 78,
  },
  good: {
    overall: 52,
    clarity: 55,
    focus: 48,
    efficiency: 53,
    label: "good",
    comment: "Solid middle-of-the-road — explained most concepts clearly, lost time on one long tangent.",
    time_saved_min: 45,
  },
  great: {
    overall: 71,
    clarity: 74,
    focus: 68,
    efficiency: 71,
    label: "great",
    comment: "Used the Timmy-buys-oranges framing before naming the function — nice one.",
    time_saved_min: 22,
  },
  excellent: {
    overall: 89,
    clarity: 92,
    focus: 88,
    efficiency: 87,
    label: "excellent",
    comment: "Every concept built from a concrete example. Watch this lecture twice.",
    time_saved_min: 8,
  },
};

export default function ScorePreviewPage() {
  const [label, setLabel] = useState<LectureScoreLabel>("ok");
  const score = MOCKS[label];

  return (
    <div className="min-h-screen py-12 px-4" style={{ background: "var(--bg)" }}>
      <div className="max-w-2xl mx-auto">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold mb-2" style={{ color: "var(--text-primary)" }}>
            Lecture Score — dev preview
          </h1>
          <p className="text-sm mb-4" style={{ color: "var(--text-secondary)" }}>
            Click <strong>Preview</strong> to open the shareable PNG, or{" "}
            <strong>Share</strong> to trigger Web Share API / clipboard fallback.
          </p>
          <div className="flex items-center justify-center gap-2 flex-wrap">
            {(Object.keys(MOCKS) as LectureScoreLabel[]).map((k) => (
              <button
                key={k}
                onClick={() => setLabel(k)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all"
                style={{
                  background: label === k ? "var(--accent-dim)" : "transparent",
                  color: label === k ? "var(--accent)" : "var(--text-muted)",
                  border: "1px solid var(--border)",
                }}
              >
                {k} ({MOCKS[k].overall})
              </button>
            ))}
          </div>
        </div>
        <LectureScoreCard
          lectureScore={score}
          transcript={mockTranscript}
          sessionName={`Microbiology Lecture 3 · ${label}`}
        />
      </div>
    </div>
  );
}
