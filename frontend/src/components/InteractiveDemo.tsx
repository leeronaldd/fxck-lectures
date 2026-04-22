"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { SlideCardGroup } from "./SlideCard";
import NarrativeSection from "./NarrativeSection";
import ImageLightbox from "./ImageLightbox";
import { TCA_DEMO_SLIDES, TCA_DEMO_TRANSCRIPT } from "@/lib/tca-demo";

type Phase = "idle" | "upload" | "processing" | "result";

const UPLOAD_MS = 12000;
const PROCESSING_MS = 3000;
const FRAME_HEIGHT_MOBILE = 520;
const FRAME_HEIGHT_DESKTOP = 640;

export default function InteractiveDemo() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);

  const startDemo = useCallback(() => setPhase("upload"), []);
  const startProcessing = useCallback(() => setPhase("processing"), []);

  // Upload → processing is fully user-driven (user clicks files then Generate).
  // Only processing → result is auto-timed.
  useEffect(() => {
    if (phase !== "processing") return;
    const t = setTimeout(() => setPhase("result"), PROCESSING_MS);
    return () => clearTimeout(t);
  }, [phase]);

  return (
    <div
      className="rounded-xl overflow-hidden shadow-2xl"
      style={{ border: "1px solid var(--border)", background: "var(--bg-elevated)" }}
    >
      {lightboxSrc && (
        <ImageLightbox src={lightboxSrc} onClose={() => setLightboxSrc(null)} />
      )}

      {/* Browser chrome */}
      <div
        className="flex items-center gap-2 px-4 py-2.5"
        style={{ borderBottom: "1px solid var(--border)" }}
      >
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full" style={{ background: "#ff5f57" }} />
          <div className="w-3 h-3 rounded-full" style={{ background: "#febc2e" }} />
          <div className="w-3 h-3 rounded-full" style={{ background: "#28c840" }} />
        </div>
        <div
          className="flex-1 mx-4 text-[11px] font-mono text-center px-3 py-1 rounded-md truncate"
          style={{ background: "var(--bg-base)", color: "var(--text-muted)" }}
        >
          {phase === "idle" && "klareai.com"}
          {phase === "upload" && "klareai.com/upload"}
          {phase === "processing" && "klareai.com/processing"}
          {phase === "result" && "klareai.com/reader"}
        </div>
      </div>

      {/* Body — fixed-height frame; result phase scrolls internally */}
      <div className="demo-frame-body relative" style={{ height: FRAME_HEIGHT_MOBILE }}>
        {phase === "idle" && <IdlePhase onStart={startDemo} />}
        {phase === "upload" && <UploadPhase onGenerate={startProcessing} />}
        {phase === "processing" && <ProcessingPhase />}
        {phase === "result" && <ResultPhase onImageClick={setLightboxSrc} />}
      </div>

      <style jsx>{`
        @media (min-width: 640px) {
          .demo-frame-body {
            height: ${FRAME_HEIGHT_DESKTOP}px !important;
          }
        }
      `}</style>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Phase 0: Idle (starts here, user must click to begin)
// ─────────────────────────────────────────────────────────────

function IdlePhase({ onStart }: { onStart: () => void }) {
  return (
    <div className="h-full relative overflow-hidden" style={{ background: "var(--bg-base)" }}>
      {/* Background: dimmed upload preview so user sees what's coming */}
      <div className="absolute inset-0 opacity-40 pointer-events-none" aria-hidden>
        <div className="h-full px-5 sm:px-10 py-8 sm:py-10 flex flex-col">
          <div className="max-w-xl mx-auto w-full">
            <h3 className="text-base sm:text-lg font-semibold mb-1" style={{ color: "var(--text-primary)" }}>
              Upload your lecture
            </h3>
            <p className="text-xs sm:text-sm mb-5" style={{ color: "var(--text-muted)" }}>
              Drop a recording + slides. We'll do the rest.
            </p>
            <div
              className="rounded-2xl border-2 border-dashed px-4 py-8 text-center"
              style={{ borderColor: "var(--border)", background: "var(--bg-surface)" }}
            >
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-2"
                style={{ background: "var(--accent-dim)", color: "var(--accent)" }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17,8 12,3 7,8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>
              <p className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>Drop files here</p>
            </div>
          </div>
        </div>
      </div>

      {/* Center CTA */}
      <div
        className="absolute inset-0 flex flex-col items-center justify-center z-10 px-6"
        style={{ background: "radial-gradient(ellipse at center, rgba(15,17,20,0) 0%, rgba(15,17,20,0.55) 60%, rgba(15,17,20,0.75) 100%)" }}
      >
        <button
          type="button"
          onClick={onStart}
          className="idle-cta-btn flex items-center gap-2.5 px-6 py-3.5 sm:px-8 sm:py-4 rounded-full text-sm sm:text-base font-bold transition-all active:scale-95"
          style={{
            background: "linear-gradient(135deg, var(--accent), #FF8555)",
            color: "#fff",
            boxShadow: "0 10px 40px var(--accent-glow), 0 0 0 6px rgba(255, 107, 53, 0.12)",
            border: "none",
            cursor: "pointer",
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <path d="M8 5v14l11-7z" />
          </svg>
          See how it works!
        </button>
      </div>

      <style jsx>{`
        .idle-cta-btn {
          animation: idle-cta-pulse 2.4s ease-in-out infinite;
        }
        @keyframes idle-cta-pulse {
          0%, 100% {
            box-shadow: 0 10px 40px rgba(255, 107, 53, 0.4), 0 0 0 6px rgba(255, 107, 53, 0.12);
            transform: scale(1);
          }
          50% {
            box-shadow: 0 14px 52px rgba(255, 107, 53, 0.55), 0 0 0 12px rgba(255, 107, 53, 0.08);
            transform: scale(1.03);
          }
        }
      `}</style>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Phase 1: Upload (12s — file explorer popup + slow cursor)
// ─────────────────────────────────────────────────────────────

function UploadPhase({ onGenerate }: { onGenerate: () => void }) {
  const [videoSelected, setVideoSelected] = useState(false);
  const [pdfSelected, setPdfSelected] = useState(false);
  const canGenerate = videoSelected && pdfSelected;

  return (
    <div
      className="h-full px-5 sm:px-10 py-8 sm:py-10 relative overflow-hidden flex flex-col"
      style={{ background: "var(--bg-base)" }}
    >
      <div className="max-w-xl mx-auto w-full">
        <h3 className="text-base sm:text-lg font-semibold mb-1" style={{ color: "var(--text-primary)" }}>
          Upload your lecture
        </h3>
        <p className="text-xs sm:text-sm mb-5" style={{ color: "var(--text-muted)" }}>
          Pick your files from the Finder →
        </p>

        {/* Dropzone */}
        <div
          className="rounded-2xl border-2 border-dashed px-4 py-6 text-center transition-all"
          style={{ borderColor: "var(--border)", background: "var(--bg-surface)" }}
        >
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-2"
            style={{ background: "var(--accent-dim)", color: "var(--accent)" }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17,8 12,3 7,8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>
          <p className="text-xs font-medium mb-0.5" style={{ color: "var(--text-primary)" }}>
            Selected files
          </p>
          <p className="text-[11px]" style={{ color: "var(--text-muted)" }}>
            mp4, mov, mp3 · PDFs optional
          </p>

          {/* Chips appear only after user clicks each file in the Finder */}
          <div className="mt-5 space-y-2 text-left min-h-[120px]">
            {videoSelected && <FileChip name="biochem-lecture.mp4" size="487 MB" icon="video" />}
            {pdfSelected && <FileChip name="tca-slides.pdf" size="3.2 MB" icon="pdf" />}
            {!videoSelected && !pdfSelected && (
              <p className="text-[11px] italic text-center pt-8" style={{ color: "var(--text-muted)" }}>
                Waiting for file selection…
              </p>
            )}
          </div>
        </div>

        {/* Generate button — disabled until both files selected */}
        <div className="mt-5 flex justify-end items-center gap-3 relative">
          {canGenerate && (
            <div
              className="generate-hint inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-bold shrink-0"
              style={{
                background: "var(--accent)",
                color: "#fff",
                boxShadow: "0 6px 20px rgba(255, 107, 53, 0.4)",
              }}
              aria-hidden
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" style={{ transform: "rotate(-20deg)" }}>
                <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z" />
              </svg>
              Click Generate
            </div>
          )}
          <button
            type="button"
            onClick={canGenerate ? onGenerate : undefined}
            disabled={!canGenerate}
            className="px-5 py-2.5 rounded-xl text-sm font-semibold transition-all"
            style={{
              background: canGenerate
                ? "linear-gradient(135deg, var(--accent), #FF8555)"
                : "var(--bg-elevated)",
              color: canGenerate ? "#fff" : "var(--text-muted)",
              boxShadow: canGenerate ? "0 8px 24px var(--accent-glow)" : "none",
              cursor: canGenerate ? "pointer" : "not-allowed",
              border: canGenerate ? "none" : "1px solid var(--border)",
              animation: canGenerate ? "demo-btn-pulse 1.8s ease-in-out infinite" : "none",
            }}
          >
            Generate →
          </button>
        </div>
      </div>

      {/* Mini Finder popup with clickable file rows */}
      <FileExplorerPopup
        videoSelected={videoSelected}
        pdfSelected={pdfSelected}
        onSelectVideo={() => setVideoSelected(true)}
        onSelectPdf={() => setPdfSelected(true)}
      />

      {/* Static click hints — rendered only while the target is the next action */}
      {!videoSelected && (
        <ClickCursorHint style={{ top: "31%", left: "80%" }} />
      )}
      {videoSelected && !pdfSelected && (
        <ClickCursorHint style={{ top: "41%", left: "80%" }} />
      )}
      {canGenerate && (
        <ClickCursorHint style={{ bottom: "14%", right: "13%", left: "auto", top: "auto" }} />
      )}

      <style jsx global>{`
        @keyframes demo-btn-pulse {
          0%, 100% {
            box-shadow: 0 8px 24px var(--accent-glow), 0 0 0 0 rgba(255, 107, 53, 0.4);
          }
          50% {
            box-shadow: 0 10px 32px var(--accent-glow), 0 0 0 10px rgba(255, 107, 53, 0);
          }
        }
        .generate-hint {
          animation: generate-hint-bob 1.2s ease-in-out infinite;
        }
        @keyframes generate-hint-bob {
          0%, 100% { transform: translateX(0); }
          50% { transform: translateX(-4px); }
        }
      `}</style>
    </div>
  );
}

/** Static cursor hint pointing at the next clickable target, gently pulsing. */
function ClickCursorHint({ style }: { style: React.CSSProperties }) {
  return (
    <div
      className="click-cursor-hint absolute z-20 pointer-events-none"
      aria-hidden
      style={{
        ...style,
        filter: "drop-shadow(0 3px 8px rgba(0, 0, 0, 0.55))",
        animation: "click-cursor-hint-pulse 1.3s ease-in-out infinite",
      }}
    >
      <svg width="26" height="26" viewBox="0 0 24 24" fill="black" stroke="white" strokeWidth="1.4">
        <path d="M3 3l7.07 17.07L12.5 13l7.07-2.43L3 3z" />
      </svg>
    </div>
  );
}

function FileExplorerPopup({
  videoSelected,
  pdfSelected,
  onSelectVideo,
  onSelectPdf,
}: {
  videoSelected: boolean;
  pdfSelected: boolean;
  onSelectVideo: () => void;
  onSelectPdf: () => void;
}) {
  return (
    <div
      className="absolute z-10"
      style={{
        top: "20%",
        right: "6%",
        width: "230px",
        background: "var(--bg-elevated)",
        border: "1px solid var(--border)",
        borderRadius: "10px",
        boxShadow: "0 20px 50px rgba(0, 0, 0, 0.45)",
        overflow: "hidden",
        opacity: 1,
      }}
    >
      {/* Finder header */}
      <div
        className="px-3 py-2 flex items-center gap-2"
        style={{ background: "var(--bg-surface)", borderBottom: "1px solid var(--border)" }}
      >
        <div className="flex gap-1">
          <div className="w-2 h-2 rounded-full" style={{ background: "#ff5f57" }} />
          <div className="w-2 h-2 rounded-full" style={{ background: "#febc2e" }} />
          <div className="w-2 h-2 rounded-full" style={{ background: "#28c840" }} />
        </div>
        <span className="text-[10px] font-medium mx-auto pr-4" style={{ color: "var(--text-secondary)" }}>
          Documents
        </span>
      </div>

      {/* File list — clickable rows */}
      <div className="py-1.5">
        <FinderRow
          label="biochem-lecture.mp4"
          size="487 MB"
          iconColor="#8b5cf6"
          iconBg="rgba(139, 92, 246, 0.15)"
          icon={
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="23 7 16 12 23 17 23 7" />
              <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
            </svg>
          }
          selected={videoSelected}
          highlightNext={!videoSelected}
          onClick={onSelectVideo}
        />
        <FinderRow
          label="tca-slides.pdf"
          size="3.2 MB"
          iconColor="#ef4444"
          iconBg="rgba(239, 68, 68, 0.15)"
          icon={
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
          }
          selected={pdfSelected}
          highlightNext={videoSelected && !pdfSelected}
          onClick={onSelectPdf}
          disabled={!videoSelected}
        />
        <div className="flex items-center gap-2 px-3 py-1.5 text-[11px]" style={{ opacity: 0.35 }}>
          <div className="w-6 h-6 rounded flex items-center justify-center shrink-0" style={{ background: "var(--bg-surface)", color: "var(--text-muted)" }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
            </svg>
          </div>
          <span className="flex-1 truncate" style={{ color: "var(--text-muted)" }}>
            lecture-notes.docx
          </span>
        </div>
      </div>

    </div>
  );
}

function FinderRow({
  label,
  size,
  icon,
  iconBg,
  iconColor,
  selected,
  highlightNext,
  disabled = false,
  onClick,
}: {
  label: string;
  size: string;
  icon: React.ReactNode;
  iconBg: string;
  iconColor: string;
  selected: boolean;
  highlightNext: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={disabled || selected ? undefined : onClick}
      disabled={disabled || selected}
      className="finder-row flex items-center gap-2 px-3 py-1.5 text-[11px] w-full text-left transition-colors"
      style={{
        background: highlightNext ? "var(--accent-dim)" : "transparent",
        cursor: disabled ? "not-allowed" : selected ? "default" : "pointer",
        opacity: disabled ? 0.4 : 1,
        animation: highlightNext ? "finder-row-pulse 1.3s ease-in-out infinite" : "none",
      }}
    >
      <div
        className="w-6 h-6 rounded flex items-center justify-center shrink-0"
        style={{ background: iconBg, color: iconColor }}
      >
        {icon}
      </div>
      <span className="flex-1 truncate" style={{ color: "var(--text-primary)" }}>
        {label}
      </span>
      {selected ? (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      ) : (
        <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>{size}</span>
      )}
    </button>
  );
}

function FileChip({
  name,
  size,
  icon,
}: {
  name: string;
  size: string;
  icon: "video" | "pdf";
}) {
  return (
    <div
      className="file-chip flex items-center gap-3 px-3 py-2 rounded-lg"
      style={{
        background: "var(--bg-elevated)",
        border: "1px solid var(--border)",
        animation: "file-chip-in 0.45s ease-out",
      }}
    >
      <div
        className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
        style={{
          background: icon === "video" ? "rgba(139, 92, 246, 0.15)" : "rgba(239, 68, 68, 0.15)",
          color: icon === "video" ? "#8b5cf6" : "#ef4444",
        }}
      >
        {icon === "video" ? (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="23 7 16 12 23 17 23 7" />
            <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
          </svg>
        ) : (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-xs font-medium truncate" style={{ color: "var(--text-primary)" }}>
          {name}
        </div>
        <div className="text-[11px]" style={{ color: "var(--text-muted)" }}>
          {size}
        </div>
      </div>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="20 6 9 17 4 12" />
      </svg>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Phase 2: Processing (10s)
// ─────────────────────────────────────────────────────────────

interface Step {
  label: string;
  detail: string;
  startMs: number;
  completeMs: number;
}

const STEPS: Step[] = [
  { label: "Transcribing audio",      detail: "2,955 words",       startMs: 0,    completeMs: 500  },
  { label: "Extracting slide frames", detail: "14 unique slides",  startMs: 500,  completeMs: 1000 },
  { label: "Mapping topics",          detail: "8-step mechanism",  startMs: 1000, completeMs: 1500 },
  { label: "Writing explanations",    detail: "14 sections",       startMs: 1500, completeMs: 2200 },
  { label: "Fact-checking claims",    detail: "OpenStax + NCBI",   startMs: 2200, completeMs: 2700 },
  { label: "Done",                    detail: "",                  startMs: 2700, completeMs: 2900 },
];

function ProcessingPhase() {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const start = performance.now();
    let raf = 0;
    const tick = () => {
      setElapsed(performance.now() - start);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  const progress = Math.min(1, elapsed / PROCESSING_MS);

  return (
    <div
      className="h-full px-6 sm:px-10 py-8 sm:py-12 flex items-center"
      style={{ background: "var(--bg-base)" }}
    >
      <div className="max-w-md mx-auto w-full">
        <div className="mb-6 text-center">
          <div
            className="w-12 h-12 rounded-full border-2 border-t-transparent animate-spin mx-auto mb-4"
            style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}
          />
          <h3 className="text-base sm:text-lg font-semibold mb-1" style={{ color: "var(--text-primary)" }}>
            Building your lecture
          </h3>
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            This takes ~5 minutes for a real lecture
          </p>
        </div>

        <div className="h-1 rounded-full overflow-hidden mb-5" style={{ background: "var(--bg-elevated)" }}>
          <div
            className="h-full rounded-full transition-all duration-100"
            style={{
              width: `${progress * 100}%`,
              background: "linear-gradient(90deg, var(--accent), #FF8555)",
            }}
          />
        </div>

        <div className="space-y-2">
          {STEPS.map((step, i) => {
            const status: "pending" | "active" | "done" =
              elapsed < step.startMs ? "pending" : elapsed < step.completeMs ? "active" : "done";
            return <StepRow key={i} step={step} status={status} />;
          })}
        </div>
      </div>
    </div>
  );
}

function StepRow({ step, status }: { step: Step; status: "pending" | "active" | "done" }) {
  const isLast = step.label === "Done";
  return (
    <div
      className="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all"
      style={{
        background: status === "active" ? "var(--accent-dim)" : "transparent",
        opacity: status === "pending" ? 0.35 : 1,
      }}
    >
      <div className="w-5 h-5 shrink-0 flex items-center justify-center">
        {status === "done" ? (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        ) : status === "active" ? (
          <div
            className="w-3.5 h-3.5 rounded-full border-2 border-t-transparent animate-spin"
            style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}
          />
        ) : (
          <div className="w-2.5 h-2.5 rounded-full" style={{ background: "var(--border)" }} />
        )}
      </div>
      <span
        className="text-sm flex-1"
        style={{
          color:
            status === "done"
              ? "var(--text-primary)"
              : status === "active"
              ? "var(--accent)"
              : "var(--text-muted)",
          fontWeight: status === "active" ? 600 : 500,
        }}
      >
        {step.label}
        {isLast && status === "done" && " ✨"}
      </span>
      {step.detail && status !== "pending" && (
        <span className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>
          {step.detail}
        </span>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Phase 3: Result — interactive info tags + scroll prompt
// ─────────────────────────────────────────────────────────────

function ResultPhase({ onImageClick }: { onImageClick: (src: string) => void }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [eiOpen, setEiOpen] = useState(false);
  const [hasScrolled, setHasScrolled] = useState(false);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onScroll = () => {
      if (el.scrollTop > 40) setHasScrolled(true);
    };
    el.addEventListener("scroll", onScroll);
    return () => el.removeEventListener("scroll", onScroll);
  }, []);

  const slideGroups: Record<number, typeof TCA_DEMO_SLIDES> = {};
  for (const card of TCA_DEMO_SLIDES) {
    const num = parseInt(card.slide_id.replace(/[a-z]/g, ""));
    if (!slideGroups[num]) slideGroups[num] = [];
    slideGroups[num].push(card);
  }

  return (
    <div
      className="result-phase h-full flex flex-col relative"
      style={{ background: "var(--bg-base)", animation: "result-fade-in 0.6s ease-out" }}
    >
      {/* Sticky header */}
      <div
        className="shrink-0 px-5 sm:px-8 py-3 flex items-center gap-3"
        style={{ borderBottom: "1px solid var(--border)", background: "var(--bg-base)" }}
      >
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
          style={{ background: "var(--accent-dim)", color: "var(--accent)" }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
            <polyline points="14,2 14,8 20,8" />
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>
            The TCA Cycle (Krebs Cycle)
          </div>
          <div className="text-[11px]" style={{ color: "var(--text-muted)" }}>
            From a 30-min MIT biochem lecture · 14 sections · ~8 min read
          </div>
        </div>
        <span
          className="hidden sm:inline-flex text-[11px] font-medium px-2 py-1 rounded-full shrink-0"
          style={{ background: "var(--accent-dim)", color: "var(--accent)" }}
        >
          Live output
        </span>
      </div>

      {/* Scrollable sections */}
      <div
        ref={scrollRef}
        className="result-scroll flex-1 overflow-y-auto overscroll-contain px-5 sm:px-8 py-5 relative"
        style={{ WebkitOverflowScrolling: "touch" as unknown as undefined }}
      >
        {/* Callouts pinned above the first slide card — left callout over the
            slide image, right callout over the EI badge. Tails point down. */}
        <div className="relative flex justify-between items-start gap-3 mb-2 px-1">
          {/* Left — just a label, no click */}
          <div
            className="comment-callout comment-tail-left static-callout relative"
            style={{ maxWidth: 200 }}
          >
            <div
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-[12px] font-semibold"
              style={{
                background: "var(--bg-surface)",
                color: "var(--accent)",
                border: "1.5px solid var(--accent)",
                boxShadow: "0 2px 8px rgba(0, 0, 0, 0.1)",
              }}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                <line x1="8" y1="21" x2="16" y2="21" />
              </svg>
              <span>Lecture extracted slide</span>
            </div>
          </div>

          {/* Right — clickable, expands to explanation */}
          <CommentCallout
            tail="right"
            isOpen={eiOpen}
            onClick={() => setEiOpen((v) => !v)}
            short={
              <>
                <span
                  className="text-[9px] font-bold px-1.5 py-0.5 rounded-full"
                  style={{ background: "rgba(255, 176, 32, 0.2)", color: "var(--ci-high)" }}
                >
                  EI
                </span>
                <span>Exam Importance %</span>
              </>
            }
            expanded={
              <p>
                <strong style={{ color: "var(--text-primary)" }}>
                  AI estimates how likely it is to be tested in exam.
                </strong>
              </p>
            }
          />
        </div>

        <div className="space-y-10">
          {TCA_DEMO_TRANSCRIPT.map((section, i) => {
            const cards = slideGroups[section.slide_number] || [];
            return (
              <div key={i}>
                {cards.length > 0 && (
                  <div className="mb-5">
                    <SlideCardGroup cards={cards} onImageClick={onImageClick} />
                    {i === 0 && (
                      <p
                        className="text-[10px] mt-2 flex items-center gap-1.5"
                        style={{ color: "var(--text-muted)" }}
                      >
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                          <line x1="8" y1="21" x2="16" y2="21" />
                        </svg>
                        Frame captured from the professor's lecture video
                      </p>
                    )}
                  </div>
                )}
                <NarrativeSection section={section} />
                {i < TCA_DEMO_TRANSCRIPT.length - 1 && (
                  <hr className="mt-10" style={{ borderColor: "var(--border)" }} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Scroll-down nudge — fades when the user actually scrolls */}
      {!hasScrolled && (
        <div
          className="scroll-nudge absolute left-1/2 -translate-x-1/2 pointer-events-none z-10"
          style={{ bottom: 18 }}
          aria-hidden
        >
          <div
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-semibold"
            style={{
              background: "var(--accent)",
              color: "#fff",
              boxShadow: "0 6px 24px rgba(255, 107, 53, 0.4)",
            }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="6 9 12 15 18 9" />
            </svg>
            Scroll down to see the quality
          </div>
        </div>
      )}

      <style jsx>{`
        @keyframes result-fade-in {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .result-scroll::-webkit-scrollbar { width: 8px; }
        .result-scroll::-webkit-scrollbar-track { background: transparent; }
        .result-scroll::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
        .result-scroll::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

        .scroll-nudge {
          animation: scroll-nudge-bounce 1.8s ease-in-out infinite;
        }
        @keyframes scroll-nudge-bounce {
          0%, 100% { transform: translate(-50%, 0); }
          50% { transform: translate(-50%, 5px); }
        }

        .callout-fade-in {
          animation: callout-fade-in 0.25s ease-out forwards;
        }
        @keyframes callout-fade-in {
          from { opacity: 0; transform: translateY(-4px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}

/** Comment-box callout: short pill that expands with a tail pointing down at content. */
function CommentCallout({
  tail,
  short,
  expanded,
  isOpen,
  onClick,
}: {
  tail: "left" | "right";
  short: React.ReactNode;
  expanded: React.ReactNode;
  isOpen: boolean;
  onClick: () => void;
}) {
  return (
    <div className={`comment-callout comment-tail-${tail} relative ${isOpen ? "is-open" : ""}`} style={{ maxWidth: isOpen ? 340 : "auto" }}>
      <button
        type="button"
        onClick={onClick}
        className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-[12px] font-semibold transition-all active:scale-95 w-full text-left"
        style={{
          background: isOpen ? "var(--accent)" : "var(--bg-surface)",
          color: isOpen ? "#fff" : "var(--accent)",
          border: `1.5px solid var(--accent)`,
          cursor: "pointer",
          boxShadow: isOpen ? "0 6px 20px rgba(255, 107, 53, 0.25)" : "0 2px 8px rgba(0, 0, 0, 0.1)",
        }}
      >
        {short}
      </button>
      {isOpen && (
        <div
          className="callout-fade-in mt-2 p-3.5 rounded-lg text-[12px] leading-relaxed"
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--accent)",
            color: "var(--text-secondary)",
          }}
        >
          {expanded}
        </div>
      )}

      <style jsx>{`
        .comment-callout {
          position: relative;
        }
        /* Downward tail on the pill */
        .comment-callout > button::after {
          content: "";
          position: absolute;
          bottom: -9px;
          width: 14px;
          height: 14px;
          background: inherit;
          border-left: 1.5px solid var(--accent);
          border-bottom: 1.5px solid var(--accent);
          transform: rotate(-45deg);
          pointer-events: none;
        }
        .comment-tail-right > button::after { right: 22px; }
        .comment-tail-left > button::after { left: 22px; }
        .comment-callout.is-open > button::after {
          background: var(--accent);
          border-color: var(--accent);
        }
      `}</style>
    </div>
  );
}
