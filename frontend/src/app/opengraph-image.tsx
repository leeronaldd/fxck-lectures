import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "Fxck Lectures — Replace Bad Professors with a 20-Min Read";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "#0F1114",
          fontFamily: "sans-serif",
          position: "relative",
        }}
      >
        {/* Subtle orange glow — no blur, just a large faded circle */}
        <div
          style={{
            position: "absolute",
            top: -80,
            right: -60,
            width: 480,
            height: 480,
            borderRadius: "50%",
            background: "rgba(255, 107, 53, 0.07)",
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: -80,
            left: -60,
            width: 380,
            height: 380,
            borderRadius: "50%",
            background: "rgba(139, 92, 246, 0.06)",
          }}
        />

        {/* Pill badge */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "8px 20px",
            borderRadius: 999,
            background: "rgba(255, 107, 53, 0.12)",
            border: "1px solid rgba(255, 107, 53, 0.3)",
            marginBottom: 32,
          }}
        >
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "#FF6B35",
            }}
          />
          <span style={{ color: "#FF6B35", fontSize: 20, fontWeight: 600 }}>
            For medical, health sci & biomed students
          </span>
        </div>

        {/* Headline — solid orange, no gradient text (Satori limitation) */}
        <div
          style={{
            fontSize: 92,
            fontWeight: 800,
            letterSpacing: "-2px",
            color: "#FF6B35",
            lineHeight: 1.05,
            textAlign: "center",
            marginBottom: 24,
          }}
        >
          Fxck Lectures
        </div>

        {/* Subheadline */}
        <div
          style={{
            fontSize: 28,
            color: "#9CA3AF",
            textAlign: "center",
            maxWidth: 780,
            lineHeight: 1.5,
            marginBottom: 56,
          }}
        >
          Turns your 2-hour lecture into a 20-minute read that actually makes sense.
        </div>

        {/* Tags row */}
        <div style={{ display: "flex", alignItems: "center", gap: 40 }}>
          {["Textbook-verified", "Exam-aware", "Free to try"].map((tag) => (
            <div
              key={tag}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                color: "#6B7280",
                fontSize: 22,
              }}
            >
              <div
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: "#FF6B35",
                }}
              />
              {tag}
            </div>
          ))}
        </div>

        {/* Watermark */}
        <div
          style={{
            position: "absolute",
            bottom: 28,
            right: 44,
            color: "rgba(255,255,255,0.18)",
            fontSize: 20,
            fontWeight: 500,
          }}
        >
          klareai.com
        </div>
      </div>
    ),
    { ...size }
  );
}
