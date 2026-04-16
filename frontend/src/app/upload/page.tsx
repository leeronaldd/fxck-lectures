"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import * as Progress from "@radix-ui/react-progress";
import { useAppStore } from "@/lib/store";
import UploadZone from "@/components/UploadZone";
import PipelineStepper from "@/components/PipelineStepper";

export default function UploadPage() {
  const router = useRouter();

  const {
    user,
    transcriptFile,
    videoFile,
    slidesFile,
    slidesFiles,
    setTranscriptFile,
    setVideoFile,
    setSlidesFile,
    setSlidesFiles,
    startPipeline,
    pipelineRuns,
    activePipelineId,
  } = useAppStore();

  // Get the active run for this page (the one we started, or any in-progress one)
  const activeRun = activePipelineId
    ? pipelineRuns[activePipelineId]
    : Object.values(pipelineRuns).find((r) => r.isProcessing || r.isDone);

  const isRunning = activeRun?.isProcessing ?? false;
  const isDone = activeRun?.isDone ?? false;
  const pipelineError = activeRun?.error ?? null;
  const isTimeout = pipelineError === "__timeout__";
  // Network drop = SSE connection lost mid-run (pipeline still running on server)
  const isNetworkDrop = !isTimeout && !!pipelineError && (
    pipelineError.toLowerCase().includes("network error") ||
    pipelineError.toLowerCase().includes("failed to fetch") ||
    pipelineError.toLowerCase().includes("connection lost") ||
    pipelineError.toLowerCase().includes("load failed")
  );
  const isBackgroundRun = isTimeout || isNetworkDrop;
  const isUploading = activeRun?.isUploading ?? false;
  const uploadProgress = activeRun?.uploadProgress ?? 0;
  const stages = activeRun?.stages ?? [];
  const currentStageIndex = activeRun?.currentStageIndex ?? -1;
  const subProgress = activeRun?.subProgress ?? 0;

  // Auto-navigate to reader when pipeline finishes with full output.
  // No early redirect on streaming sections — the 30s time saving isn't
  // worth the UX issues (lost state, wrong page, manual navigation).
  useEffect(() => {
    if (isDone) {
      const t = setTimeout(() => router.push("/reader"), 600);
      return () => clearTimeout(t);
    }
  }, [isDone, router]);

  const hasFile = transcriptFile || videoFile;
  const showProgress = isRunning || isDone || !!pipelineError;

  return (
    <div className="flex-1 relative overflow-hidden overflow-y-auto">
      <div className="hero-glow hero-glow-pulse" />

      <div className="relative z-10 max-w-lg mx-auto px-4 sm:px-6 pt-10 sm:pt-16 pb-16">

        {!showProgress ? (
          <>
            {/* Upload form */}
            <div className="text-center mb-8">
              <h1 className="text-2xl sm:text-3xl font-bold mb-2" style={{ color: "var(--text-primary)" }}>
                {user.isLoggedIn ? `Welcome back, ${user.name.split(" ")[0]}` : "Transform a lecture"}
              </h1>
              <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                Drop your lecture recording or transcript and we'll rewrite it as a tutor-quality read.
              </p>
            </div>

            <div className="glass rounded-2xl p-6 sm:p-8">
              <UploadZone
                videoFile={videoFile}
                transcriptFile={transcriptFile}
                slidesFile={slidesFile}
                slidesFiles={slidesFiles}
                onVideoChange={setVideoFile}
                onTranscriptChange={setTranscriptFile}
                onSlidesChange={setSlidesFile}
                onSlidesFilesChange={setSlidesFiles}
                uploadProgress={uploadProgress}
                isUploading={isUploading}
              />

              <button
                onClick={() => startPipeline()}
                disabled={!hasFile}
                className="btn-glow w-full mt-6 py-3.5 px-6 rounded-xl text-sm font-semibold transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                style={{
                  background: hasFile
                    ? "linear-gradient(135deg, var(--accent), #FF8555)"
                    : "var(--bg-elevated)",
                  color: hasFile ? "#fff" : "var(--text-muted)",
                  boxShadow: hasFile ? "0 8px 32px var(--accent-glow)" : "none",
                }}
              >
                Transform Lecture
              </button>

              <p className="text-center text-xs mt-4" style={{ color: "var(--text-muted)" }}>
                Supports .mp4/.mp3 lecture recordings and .txt transcripts
              </p>
            </div>
          </>
        ) : (
          <>
            {/* Inline progress — same page, no navigation */}
            <div className="text-center mb-8">
              <div className="mb-4 flex justify-center">
                {isBackgroundRun ? (
                  <div className="w-14 h-14 rounded-2xl flex items-center justify-center"
                    style={{ background: "var(--accent-dim)", border: "1px solid rgba(255, 107, 53, 0.2)" }}>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10" /><polyline points="12,6 12,12 16,14" />
                    </svg>
                  </div>
                ) : pipelineError ? (
                  <div className="w-14 h-14 rounded-2xl flex items-center justify-center"
                    style={{ background: "rgba(255, 68, 68, 0.1)", border: "1px solid rgba(255, 68, 68, 0.2)" }}>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FF4444" strokeWidth="2" strokeLinecap="round">
                      <circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
                    </svg>
                  </div>
                ) : isDone ? (
                  <div className="w-14 h-14 rounded-2xl flex items-center justify-center"
                    style={{ background: "rgba(74, 222, 128, 0.1)", border: "1px solid rgba(74, 222, 128, 0.2)" }}>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#4ade80" strokeWidth="2" strokeLinecap="round">
                      <path d="M20 6L9 17l-5-5" />
                    </svg>
                  </div>
                ) : (
                  <div className="w-14 h-14 rounded-2xl flex items-center justify-center animate-spin-slow"
                    style={{ background: "var(--accent-dim)", border: "1px solid rgba(255, 107, 53, 0.2)" }}>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round">
                      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                    </svg>
                  </div>
                )}
              </div>

              <h1 className="text-xl font-bold mb-1" style={{ color: pipelineError ? "#FF6666" : "var(--text-primary)" }}>
                {isBackgroundRun ? "Your lecture is being rebuilt..." : pipelineError ? "Something went wrong" : isDone ? "Ready!" : isUploading ? "Uploading your lecture..." : "Transforming your lecture..."}
              </h1>
              <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                {isBackgroundRun
                  ? "This usually takes 8–10 minutes. Feel free to close this tab — we'll save it to your sessions when it's ready."
                  : pipelineError
                    ? pipelineError
                    : isDone
                      ? "Taking you to your lecture..."
                      : isUploading
                        ? "Stay on this page until the upload finishes — navigating away may interrupt it."
                        : "This usually takes a few minutes. You can switch tabs — it'll keep going."}
              </p>
            </div>

            <div className="glass rounded-2xl p-6">
              {isUploading ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>Uploading...</span>
                    <span className="text-sm font-mono" style={{ color: "var(--accent)" }}>{uploadProgress}%</span>
                  </div>
                  <Progress.Root className="relative overflow-hidden rounded-full w-full h-2" style={{ background: "var(--bg-elevated)" }} value={uploadProgress}>
                    <Progress.Indicator
                      className="w-full h-full rounded-full transition-transform duration-300 ease-out"
                      style={{
                        background: "linear-gradient(90deg, var(--accent), #FF8555)",
                        transform: `translateX(-${100 - uploadProgress}%)`,
                        boxShadow: "0 0 12px var(--accent-glow)",
                      }}
                    />
                  </Progress.Root>
                </div>
              ) : (
                <PipelineStepper stages={stages} currentStageIndex={currentStageIndex} subProgress={subProgress} />
              )}
            </div>

            {/* Actions */}
            <div className="mt-6 flex justify-center gap-3">
              {isBackgroundRun && (
                <>
                  <button
                    onClick={async () => {
                      await useAppStore.getState().loadSessions();
                      const sessions = useAppStore.getState().sessions;
                      if (sessions.length > 0) {
                        await useAppStore.getState().loadSession(sessions[0].id);
                      }
                      router.push("/reader");
                    }}
                    className="btn-glow px-6 py-2.5 text-sm font-semibold rounded-xl"
                    style={{ background: "linear-gradient(135deg, var(--accent), #FF8555)", color: "#fff", boxShadow: "0 8px 32px var(--accent-glow)" }}
                  >
                    Check sessions
                  </button>
                  <button
                    onClick={() => { useAppStore.getState().reset(); }}
                    className="px-4 py-2 text-sm rounded-xl"
                    style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}
                  >
                    Upload new file
                  </button>
                </>
              )}
              {pipelineError && !isBackgroundRun && (
                <button
                  onClick={() => { useAppStore.getState().reset(); }}
                  className="btn-glow px-6 py-2.5 text-sm font-semibold rounded-xl"
                  style={{ background: "linear-gradient(135deg, var(--accent), #FF8555)", color: "#fff", boxShadow: "0 8px 32px var(--accent-glow)" }}
                >
                  Try Again
                </button>
              )}
              {!isDone && !pipelineError && (
                <button
                  onClick={() => { useAppStore.getState().cancelPipeline(); useAppStore.getState().reset(); }}
                  className="px-4 py-2 text-sm rounded-xl"
                  style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}
                >
                  Cancel
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
