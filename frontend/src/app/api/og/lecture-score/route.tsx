import { ImageResponse } from "next/og";
import type { NextRequest } from "next/server";

export const runtime = "edge";

function clamp(n: number, min = 0, max = 100) {
  return Math.max(min, Math.min(max, n));
}

// 5-tier colour scale — must match LectureScoreCard.LABEL_COLORS
const LABEL_COLORS = {
  rough: "#ef4444",
  ok: "#f97316",
  good: "#eab308",
  great: "#84cc16",
  excellent: "#22c55e",
} as const;

type Label = keyof typeof LABEL_COLORS;

function labelForScore(overall: number): Label {
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

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);

  const overall = clamp(parseInt(searchParams.get("overall") || "35"));
  const clarity = clamp(parseInt(searchParams.get("clarity") || "30"));
  const focus = clamp(parseInt(searchParams.get("focus") || "40"));
  const efficiency = clamp(parseInt(searchParams.get("efficiency") || "28"));
  const comment =
    searchParams.get("comment") ||
    searchParams.get("roast") || // legacy param name
    "Spent 20 minutes on a concept worth 2 sentences.";
  const sessionName = searchParams.get("name") || "Lecture 3";
  const timeSaved = parseInt(searchParams.get("time_saved") || "0");

  // Trust URL label if valid, else derive from overall
  const rawLabel = (searchParams.get("label") || "").toLowerCase() as Label;
  const label: Label =
    rawLabel in LABEL_COLORS ? rawLabel : labelForScore(overall);

  const overallColor = LABEL_COLORS[label];

  const Bar = ({ name, value }: { name: string; value: number }) => (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 18,
        width: "100%",
      }}
    >
      <div style={{ display: "flex", fontSize: 22, color: "#9ca3af", width: 150 }}>
        {name}
      </div>
      <div
        style={{
          flex: 1,
          height: 14,
          background: "#1f2937",
          borderRadius: 999,
          display: "flex",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${value}%`,
            height: "100%",
            background: barColor(value),
            borderRadius: 999,
          }}
        />
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          fontSize: 24,
          color: "#f3f4f6",
          fontFamily: "monospace",
          width: 70,
        }}
      >
        {`${value}%`}
      </div>
    </div>
  );

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          background:
            "linear-gradient(135deg, #0a0a0a 0%, #1a0f0a 50%, #0f0a14 100%)",
          padding: "40px 56px",
          fontFamily: "system-ui, -apple-system, sans-serif",
          color: "#f3f4f6",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 8,
          }}
        >
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div
              style={{
                display: "flex",
                fontSize: 22,
                color: "#9ca3af",
                fontWeight: 500,
                marginBottom: 2,
              }}
            >
              Lecture Score
            </div>
            <div style={{ display: "flex", fontSize: 16, color: "#6b7280" }}>
              {sessionName}
            </div>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "8px 16px",
              background: "rgba(255, 107, 53, 0.15)",
              borderRadius: 10,
              border: "1px solid rgba(255, 107, 53, 0.3)",
            }}
          >
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: 999,
                background: "#ff6b35",
              }}
            />
            <div
              style={{
                display: "flex",
                fontSize: 18,
                color: "#ff6b35",
                fontWeight: 600,
              }}
            >
              Klare
            </div>
          </div>
        </div>

        {/* Big score */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            marginTop: 8,
            marginBottom: 20,
          }}
        >
          <div
            style={{
              fontSize: 130,
              fontWeight: 800,
              color: overallColor,
              lineHeight: 1,
              letterSpacing: "-0.05em",
              display: "flex",
              alignItems: "baseline",
            }}
          >
            {overall}
            <span style={{ fontSize: 52, color: "#6b7280", fontWeight: 500 }}>
              /100
            </span>
          </div>
          <div
            style={{
              display: "flex",
              fontSize: 24,
              color: overallColor,
              marginTop: 6,
              textTransform: "capitalize",
              fontWeight: 600,
            }}
          >
            {label}
          </div>
        </div>

        {/* Bars */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 14,
            marginBottom: 22,
          }}
        >
          <Bar name="Clarity" value={clarity} />
          <Bar name="Focus" value={focus} />
          <Bar name="Efficiency" value={efficiency} />
        </div>

        {/* Comment */}
        <div
          style={{
            display: "flex",
            fontSize: 24,
            color: "#e5e7eb",
            fontStyle: "italic",
            padding: "16px 22px",
            background: "rgba(0, 0, 0, 0.3)",
            borderLeft: `4px solid ${overallColor}99`,
            borderRadius: "0 10px 10px 0",
            lineHeight: 1.3,
          }}
        >
          {`“${comment}”`}
        </div>

        {/* Footer */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginTop: "auto",
            paddingTop: 16,
          }}
        >
          <div style={{ display: "flex", fontSize: 20, color: "#6b7280" }}>
            {timeSaved > 0 ? `Klare saved ~${timeSaved} min` : "Survived with Klare"}
          </div>
          <div
            style={{
              display: "flex",
              fontSize: 22,
              color: "#ff6b35",
              fontWeight: 600,
            }}
          >
            klareai.com
          </div>
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    }
  );
}
