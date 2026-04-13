"use client";

const SUGGESTIONS = [
  {
    title: "Got a lecture transcript?",
    body: "Paste or upload a .txt file and I'll turn it into a proper study doc.",
    icon: "📄",
  },
  {
    title: "Have a lecture recording?",
    body: "Drop an .mp4 or .mp3 and I'll transcribe + teach it from scratch.",
    icon: "🎥",
  },
  {
    title: "Bad professor syndrome?",
    body: "If they ramble, skip slides, or just read off notes — I fix all that.",
    icon: "😤",
  },
  {
    title: "Exam coming up?",
    body: "I highlight exactly what's exam-worthy and what's irrelevant filler.",
    icon: "📝",
  },
];

interface Props {
  onSuggestionClick?: (title: string) => void;
}

export default function SuggestedActions({ onSuggestionClick }: Props) {
  return (
    <div className="w-full max-w-3xl mx-auto mt-8">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {SUGGESTIONS.map((s, i) => (
          <button
            key={i}
            onClick={() => onSuggestionClick?.(s.title)}
            className="text-left p-4 rounded-2xl transition-all group"
            style={{
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.07)",
              animationDelay: `${i * 60}ms`,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "rgba(255,255,255,0.06)";
              e.currentTarget.style.borderColor = "rgba(255,255,255,0.12)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "rgba(255,255,255,0.03)";
              e.currentTarget.style.borderColor = "rgba(255,255,255,0.07)";
            }}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-semibold mb-1 truncate" style={{ color: "var(--text-primary)" }}>
                  {s.title}
                </p>
                <p className="text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
                  {s.body}
                </p>
              </div>
              <svg
                width="14" height="14" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2" strokeLinecap="round"
                className="shrink-0 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity -translate-y-0.5 -translate-x-0.5"
                style={{ color: "var(--text-muted)" }}
              >
                <line x1="7" y1="17" x2="17" y2="7" />
                <polyline points="7 7 17 7 17 17" />
              </svg>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
