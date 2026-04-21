"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import * as Progress from "@radix-ui/react-progress";
import { useAppStore } from "@/lib/store";
import PipelineStepper from "@/components/PipelineStepper";

export default function ProcessingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const pipelineId = searchParams.get("id");

  const { pipelineRuns, activePipelineId, cancelPipeline } = useAppStore();

  // If a specific pipeline ID is requested, switch to it
  useEffect(() => {
    if (pipelineId && pipelineId !== activePipelineId) {
      useAppStore.setState({ activePipelineId: pipelineId });
    }
  }, [pipelineId, activePipelineId]);

  // Get the active run
  const viewId = pipelineId || activePipelineId;
  const run = viewId ? pipelineRuns[viewId] : null;

  const stages = run?.stages || [];
  const currentStageIndex = run?.currentStageIndex ?? -1;
  const subProgress = run?.subProgress ?? 0;
  const isProcessing = run?.isProcessing ?? false;
  const isDone = run?.isDone ?? false;
  const pipelineError = run?.error ?? null;
  const isUploading = run?.isUploading ?? false;
  const uploadProgress = run?.uploadProgress ?? 0;

  // Redirect to reader when done
  useEffect(() => {
    if (isDone) {
      const timer = setTimeout(() => router.push("/reader"), 500);
      return () => clearTimeout(timer);
    }
  }, [isDone, router]);

  // Redirect to upload only if there's genuinely no pipeline — not on first mount
  // (first render can race before Zustand has hydrated the active run).
  // On refresh the pipeline keeps running in the background and the result
  // gets saved to Supabase, so tell the user where to find it instead of
  // silently dropping them on /upload.
  useEffect(() => {
    if (run || pipelineError) return;
    const timer = setTimeout(() => {
      const stillNoRun = !useAppStore.getState().pipelineRuns[viewId || ""];
      if (stillNoRun) {
        if (pipelineId) {
          toast("Your lecture is still being built in the background.", {
            description: "It'll show up in Recent Sessions on the left when ready.",
            duration: 7000,
          });
        }
        router.replace("/upload");
      }
    }, 500);
    return () => clearTimeout(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run, pipelineError]);

  const handleCancel = () => {
    if (viewId) cancelPipeline(viewId);
    router.push("/upload");
  };

  return (
    <div className="flex-1 flex items-center justify-center px-4 py-12 relative overflow-hidden">
      {/* Background effects */}
      <div className="hero-glow hero-glow-pulse" />

      <div className="relative z-10 w-full max-w-lg animate-fade-in-up">
        {/* Header */}
        <div className="text-center mb-8">
          {/* Animated status icon */}
          <div className="mb-4 flex justify-center">
            {pipelineError ? (
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center"
                style={{ background: "rgba(255, 68, 68, 0.1)", border: "1px solid rgba(255, 68, 68, 0.2)" }}
              >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FF4444" strokeWidth="2" strokeLinecap="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="15" y1="9" x2="9" y2="15" />
                  <line x1="9" y1="9" x2="15" y2="15" />
                </svg>
              </div>
            ) : isDone ? (
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center"
                style={{ background: "rgba(74, 222, 128, 0.1)", border: "1px solid rgba(74, 222, 128, 0.2)" }}
              >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#4ade80" strokeWidth="2" strokeLinecap="round">
                  <path d="M20 6L9 17l-5-5" />
                </svg>
              </div>
            ) : (
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center animate-spin-slow"
                style={{ background: "var(--accent-dim)", border: "1px solid rgba(255, 107, 53, 0.2)" }}
              >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round">
                  <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                </svg>
              </div>
            )}
          </div>

          <h1
            className="text-xl font-bold mb-1"
            style={{ color: pipelineError ? "#FF6666" : "var(--text-primary)" }}
          >
            {pipelineError ? "Something went wrong" : isDone ? "Ready!" : isUploading ? "Uploading your lecture..." : "Transforming your lecture..."}
          </h1>
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
            {pipelineError
              ? pipelineError
              : isDone
                ? "Your lecture replacement is ready to read."
                : isUploading
                  ? "Sending your file to the server..."
                  : "This usually takes a few minutes. Grab a coffee."}
          </p>
        </div>

        {/* Pipeline card */}
        <div className="glass rounded-2xl p-6">
          {isUploading ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                  Uploading...
                </span>
                <span className="text-sm font-mono" style={{ color: "var(--accent)" }}>
                  {uploadProgress}%
                </span>
              </div>
              <Progress.Root
                className="relative overflow-hidden rounded-full w-full h-2"
                style={{ background: "var(--bg-elevated)" }}
                value={uploadProgress}
              >
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
            <PipelineStepper
              stages={stages}
              currentStageIndex={currentStageIndex}
              subProgress={subProgress}
            />
          )}
        </div>

        {/* Active pipelines count */}
        {Object.values(pipelineRuns).filter((r) => r.isProcessing).length > 1 && (
          <div className="mt-4 text-center">
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              {Object.values(pipelineRuns).filter((r) => r.isProcessing).length} lectures processing simultaneously
            </p>
          </div>
        )}

        {/* Actions */}
        <div className="mt-6 flex justify-center gap-3">
          {pipelineError && (
            <button
              onClick={() => { if (viewId) cancelPipeline(viewId); router.push("/upload"); }}
              className="btn-glow px-6 py-2.5 text-sm font-semibold rounded-xl transition-all"
              style={{
                background: "linear-gradient(135deg, var(--accent), #FF8555)",
                color: "#fff",
                boxShadow: "0 8px 32px var(--accent-glow)",
              }}
            >
              Try Again
            </button>
          )}
          {!isDone && !pipelineError && (
            <button
              onClick={handleCancel}
              className="px-4 py-2 text-sm rounded-xl transition-all"
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                color: "var(--text-secondary)",
              }}
            >
              Cancel
            </button>
          )}
          {isDone && (
            <button
              onClick={() => router.push("/reader")}
              className="btn-glow px-6 py-2.5 text-sm font-semibold rounded-xl transition-all"
              style={{
                background: "linear-gradient(135deg, var(--accent), #FF8555)",
                color: "#fff",
                boxShadow: "0 8px 32px var(--accent-glow)",
              }}
            >
              Start Reading
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
