"use client";

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
        className="w-6 h-6 rounded-full flex items-center justify-center text-xs"
        style={{ background: "#4ade80", color: "#000" }}
      >
        ✓
      </div>
    );
  }
  if (status === "running") {
    return (
      <div
        className="w-6 h-6 rounded-full border-2 border-t-transparent animate-spin"
        style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}
      />
    );
  }
  return (
    <div
      className="w-6 h-6 rounded-full border-2"
      style={{ borderColor: "var(--border)" }}
    />
  );
}

export default function PipelineStepper({
  stages,
  currentStageIndex,
  subProgress,
}: PipelineStepperProps) {
  // Calculate overall progress (weighted)
  const totalWeight = stages.reduce((sum, s) => sum + s.weight, 0);
  let completedWeight = 0;
  for (let i = 0; i < stages.length; i++) {
    if (stages[i].status === "done") {
      completedWeight += stages[i].weight;
    } else if (stages[i].status === "running") {
      // Partial progress for running stage
      if (stages[i].hasSubProgress && stages[i].subTotal) {
        completedWeight += (subProgress / (stages[i].subTotal ?? 1)) * stages[i].weight;
      } else {
        completedWeight += stages[i].weight * 0.5; // estimate 50%
      }
    }
  }
  const overallPercent = Math.round((completedWeight / totalWeight) * 100);

  return (
    <div className="space-y-6">
      {/* Overall progress bar */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
            Processing...
          </span>
          <span className="text-sm font-mono" style={{ color: "var(--accent)" }}>
            {overallPercent}%
          </span>
        </div>
        <div
          className="h-2 rounded-full overflow-hidden"
          style={{ background: "var(--bg-elevated)" }}
        >
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${overallPercent}%`,
              background: "var(--accent)",
            }}
          />
        </div>
      </div>

      {/* Stage list */}
      <div className="space-y-1">
        {stages.map((stage, i) => (
          <div
            key={i}
            className="flex items-start gap-3 py-2.5 px-3 rounded-lg transition-colors"
            style={{
              background: stage.status === "running" ? "var(--accent-dim)" : "transparent",
            }}
          >
            <StageIcon status={stage.status} />
            <div className="flex-1 min-w-0">
              <p
                className="text-sm font-medium"
                style={{
                  color:
                    stage.status === "pending"
                      ? "var(--text-muted)"
                      : "var(--text-primary)",
                }}
              >
                {stage.name}
              </p>

              {/* Sub-progress for generation */}
              {stage.status === "running" && stage.hasSubProgress && stage.subTotal && (
                <div className="mt-1.5">
                  <div className="flex items-center gap-2">
                    <div
                      className="flex-1 h-1.5 rounded-full overflow-hidden"
                      style={{ background: "var(--bg-elevated)" }}
                    >
                      <div
                        className="h-full rounded-full transition-all duration-300"
                        style={{
                          width: `${(subProgress / stage.subTotal) * 100}%`,
                          background: "var(--accent)",
                        }}
                      />
                    </div>
                    <span className="text-xs" style={{ color: "var(--text-muted)" }}>
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
