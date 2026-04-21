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
          overflow: "hidden",
        }}
      >
        {/* Orange glow blob */}
        <div
          style={{
            position: "absolute",
            top: "-120px",
            right: "-80px",
            width: "500px",
            height: "500px",
            borderRadius: "50%",
            background: "rgba(255, 107, 53, 0.18)",
            filter: "blur(80px)",
          }}
        />
        {/* Purple glow blob */}
        <div
          style={{
            position: "absolute",
            bottom: "-100px",
            left: "-60px",
            width: "400px",
            height: "400px",
            borderRadius: "50%",
            background: "rgba(139, 92, 246, 0.12)",
            filter: "blur(80px)",
          }}
        />

        {/* Pill badge */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "8px 18px",
            borderRadius: "999px",
            background: "rgba(255, 107, 53, 0.12)",
            border: "1px solid rgba(255, 107, 53, 0.25)",
            marginBottom: "28px",
          }}
        >
          <div
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              background: "#FF6B35",
            }}
          />
          <span style={{ color: "#FF6B35", fontSize: "18px", fontWeight: 600 }}>
            For medical, health sci &amp; biomed students
          </span>
        </div>

        {/* Headline */}
        <div
          style={{
            fontSize: "86px",
            fontWeight: 800,
            letterSpacing: "-2px",
            background: "linear-gradient(135deg, #FF6B35 0%, #FF8555 50%, #c084fc 100%)",
            backgroundClip: "text",
            color: "transparent",
            lineHeight: 1.05,
            textAlign: "center",
            marginBottom: "24px",
          }}
        >
          Fxck Lectures
        </div>

        {/* Subheadline */}
        <div
          style={{
            fontSize: "26px",
            color: "#9CA3AF",
            textAlign: "center",
            maxWidth: "760px",
            lineHeight: 1.5,
            marginBottom: "52px",
          }}
        >
          Turns your 2-hour lecture into a 20-minute read that actually makes sense.
        </div>

        {/* Bottom bar */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "32px",
          }}
        >
          {["Textbook-verified", "Exam-aware", "Free to try"].map((tag) => (
            <div
              key={tag}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                color: "#6B7280",
                fontSize: "20px",
              }}
            >
              <div
                style={{
                  width: "6px",
                  height: "6px",
                  borderRadius: "50%",
                  background: "#FF6B35",
                }}
              />
              {tag}
            </div>
          ))}
        </div>

        {/* klareai.com watermark */}
        <div
          style={{
            position: "absolute",
            bottom: "28px",
            right: "40px",
            color: "rgba(255,255,255,0.2)",
            fontSize: "18px",
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
