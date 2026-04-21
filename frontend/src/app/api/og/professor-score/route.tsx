import { ImageResponse } from "next/og";
import type { NextRequest } from "next/server";

export const runtime = "edge";

function clamp(n: number, min = 0, max = 100) {
  return Math.max(min, Math.min(max, n));
}

function barColor(value: number) {
  if (value < 30) return "#ef4444";
  if (value < 50) return "#f97316";
  return "#22c55e";
}

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);

  const overall = clamp(parseInt(searchParams.get("overall") || "35"));
  const clarity = clamp(parseInt(searchParams.get("clarity") || "30"));
  const focus = clamp(parseInt(searchParams.get("focus") || "40"));
  const efficiency = clamp(parseInt(searchParams.get("efficiency") || "28"));
  const roast =
    searchParams.get("roast") ||
    "Spent 20 minutes on a concept worth 2 sentences.";
  const sessionName =
    searchParams.get("name") || "Microbiology Lecture 3";

  const label =
    overall < 25
      ? "Train wreck"
      : overall < 40
      ? "Rough"
      : overall < 55
      ? "Needs work"
      : "Passable";

  const overallColor = overall < 40 ? "#ef4444" : "#f97316";

  const Bar = ({ label, value }: { label: string; value: number }) => (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 18,
        width: "100%",
      }}
    >
      <div style={{ display: "flex", fontSize: 22, color: "#9ca3af", width: 150 }}>
        {label}
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
              Professor Clarity Score
            </div>
            <div
              style={{
                display: "flex",
                fontSize: 16,
                color: "#6b7280",
              }}
            >
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
            <div style={{ display: "flex", fontSize: 18, color: "#ff6b35", fontWeight: 600 }}>
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
              fontSize: 22,
              color: "#9ca3af",
              marginTop: 6,
              fontStyle: "italic",
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
          <Bar label="Clarity" value={clarity} />
          <Bar label="Focus" value={focus} />
          <Bar label="Efficiency" value={efficiency} />
        </div>

        {/* Roast line */}
        <div
          style={{
            display: "flex",
            fontSize: 24,
            color: "#e5e7eb",
            fontStyle: "italic",
            padding: "16px 22px",
            background: "rgba(0, 0, 0, 0.3)",
            borderLeft: "4px solid rgba(239, 68, 68, 0.6)",
            borderRadius: "0 10px 10px 0",
            lineHeight: 1.3,
          }}
        >
          {`“${roast}”`}
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
            Survived with Klare
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
