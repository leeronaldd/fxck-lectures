"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";
import PipelineStepper from "@/components/PipelineStepper";

export default function ProcessingPage() {
  const router = useRouter();
  const { stages, currentStageIndex, subProgress, isProcessing, isDone, pipelineError, cancelPipeline } =
    useAppStore();

  // Redirect to reader when done
  useEffect(() => {
    if (isDone) {
      const timer = setTimeout(() => router.push("/reader"), 500);
      return () => clearTimeout(timer);
    }
  }, [isDone, router]);

  // Redirect to home only if pipeline was never started (and no error)
  useEffect(() => {
    if (!isProcessing && !isDone && !pipelineError && currentStageIndex === -1) {
      router.replace("/");
    }
  }, [isProcessing, isDone, pipelineError, currentStageIndex, router]);

  const handleCancel = () => {
    cancelPipeline();
    router.push("/");
  };

  return (
    <div className="flex-1 flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-lg">
        <div className="text-center mb-8">
          <h1
            className="text-xl font-bold mb-1"
            style={{ color: pipelineError ? "#FF4444" : "var(--text-primary)", fontFamily: "system-ui, sans-serif" }}
          >
            {pipelineError ? "Something went wrong" : isDone ? "Ready!" : "Transforming your lecture..."}
          </h1>
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
            {pipelineError
              ? pipelineError
              : isDone
                ? "Your lecture replacement is ready to read."
                : "This usually takes a few minutes. You can watch the progress below."}
          </p>
        </div>

        <div
          className="rounded-xl border p-5"
          style={{ background: "var(--bg-surface)", borderColor: "var(--border)" }}
        >
          <PipelineStepper
            stages={stages}
            currentStageIndex={currentStageIndex}
            subProgress={subProgress}
          />
        </div>

        <div className="mt-6 flex justify-center gap-3">
          {pipelineError && (
            <button
              onClick={() => { cancelPipeline(); router.push("/"); }}
              className="px-6 py-2.5 text-sm font-semibold rounded-xl transition-colors"
              style={{ background: "var(--accent)", color: "#fff" }}
            >
              Try Again
            </button>
          )}
          {!isDone && !pipelineError && (
            <button
              onClick={handleCancel}
              className="px-4 py-2 text-sm rounded-lg border transition-colors hover:bg-[var(--bg-surface)]"
              style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
            >
              Cancel
            </button>
          )}
          {isDone && (
            <button
              onClick={() => router.push("/reader")}
              className="px-6 py-2.5 text-sm font-semibold rounded-xl transition-colors"
              style={{ background: "var(--accent)", color: "#fff" }}
            >
              Start Reading
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
