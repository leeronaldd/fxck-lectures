"use client";

import * as Progress from "@radix-ui/react-progress";
import { PipelineStage } from "@/lib/store";

interface PipelineStepperProps {
  stages: PipelineStage[];
  currentStageIndex: number;
  subProgress: number;
}

function StageIcon({ status }: { status: PipelineStage["status"] }) {
  if (status === "done") {
    return (
      <div
        className="w-6 h-6 rounded-full flex items-center justify-center shrink-0"
        style={{ background: "rgba(74, 222, 128, 0.15)", color: "#4ade80" }}
      >
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <path d="M10 3L4.5 8.5 2 6" />
        </svg>
      </div>
    );
  }
  if (status === "running") {
    return (
      <div className="w-6 h-6 shrink-0 relative flex items-center justify-center">
        <div
          className="w-6 h-6 rounded-full border-2 border-t-transparent animate-spin absolute"
          style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}
        />
        <div className="w-2 h-2 rounded-full" style={{ background: "var(--accent)" }} />
      </div>
    );
  }
  return (
    <div
      className="w-6 h-6 rounded-full border-2 shrink-0"
      style={{ borderColor: "var(--border)" }}
    />
  );
}

export default function PipelineStepper({
  stages,
  currentStageIndex,
  subProgress,
}: PipelineStepperProps) {
  // If subProgress comes from the backend (0-100 overall %), use it directly
  // Otherwise calculate from stage weights
  const overallPercent = subProgress > 0
    ? Math.min(Math.round(subProgress), 100)
    : (() => {
        const totalWeight = stages.reduce((sum, s) => sum + s.weight, 0);
        let completedWeight = 0;
        for (let i = 0; i < stages.length; i++) {
          if (stages[i].status === "done") {
            completedWeight += stages[i].weight;
          } else if (stages[i].status === "running") {
            completedWeight += stages[i].weight * 0.5;
          }
        }
        return Math.min(Math.round((completedWeight / totalWeight) * 100), 100);
      })();

  return (
    <div className="space-y-6">
      {/* Overall progress bar */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
            {overallPercent === 100 ? "Complete" : "Processing..."}
          </span>
          <span className="text-sm font-mono" style={{ color: "var(--accent)" }}>
            {overallPercent}%
          </span>
        </div>
        <Progress.Root
          className="relative overflow-hidden rounded-full w-full h-2"
          style={{ background: "var(--bg-elevated)" }}
          value={overallPercent}
        >
          <Progress.Indicator
            className="w-full h-full rounded-full transition-transform duration-500 ease-out"
            style={{
              background: overallPercent === 100
                ? "linear-gradient(90deg, #4ade80, #22c55e)"
                : "linear-gradient(90deg, var(--accent), #FF8555)",
              transform: `translateX(-${100 - overallPercent}%)`,
              boxShadow: `0 0 12px ${overallPercent === 100 ? "rgba(74, 222, 128, 0.3)" : "var(--accent-glow)"}`,
            }}
          />
        </Progress.Root>
      </div>

      {/* Stage list */}
      <div className="space-y-0.5">
        {stages.map((stage, i) => (
          <div
            key={i}
            className="flex items-start gap-3 py-2.5 px-3 rounded-lg transition-all duration-300"
            style={{
              background: stage.status === "running" ? "var(--accent-dim)" : "transparent",
              opacity: stage.status === "pending" ? 0.5 : 1,
            }}
          >
            <div className="mt-0.5">
              <StageIcon status={stage.status} />
            </div>
            <div className="flex-1 min-w-0">
              <p
                className="text-sm font-medium transition-colors"
                style={{
                  color: stage.status === "pending" ? "var(--text-muted)" : "var(--text-primary)",
                }}
              >
                {stage.name}
              </p>

              {/* Sub-progress for generation */}
              {stage.status === "running" && stage.hasSubProgress && stage.subTotal && (
                <div className="mt-2">
                  <div className="flex items-center gap-2">
                    <Progress.Root
                      className="relative overflow-hidden rounded-full flex-1 h-1.5"
                      style={{ background: "var(--bg-elevated)" }}
                      value={(subProgress / stage.subTotal) * 100}
                    >
                      <Progress.Indicator
                        className="w-full h-full rounded-full transition-transform duration-300 ease-out"
                        style={{
                          background: "var(--accent)",
                          transform: `translateX(-${100 - (subProgress / stage.subTotal) * 100}%)`,
                        }}
                      />
                    </Progress.Root>
                    <span className="text-xs font-mono shrink-0" style={{ color: "var(--text-muted)" }}>
                      {subProgress}/{stage.subTotal}
                    </span>
                  </div>
                </div>
              )}

              {/* Completed result */}
              {stage.status === "done" && stage.result && (
                <p className="text-xs mt-0.5" style={{ color: "var(--text-secondary)" }}>
                  {stage.result}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
