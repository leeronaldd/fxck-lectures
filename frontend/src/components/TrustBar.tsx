"use client";

import { TrustStats } from "@/lib/types";

interface TrustBarProps {
  stats: TrustStats;
  groupCount: number;
}

export default function TrustBar({ stats, groupCount }: TrustBarProps) {
  const hasData = stats.totalClaims > 0;
  const dotColor = !hasData
    ? "var(--text-muted)"
    : stats.verifiedPercent >= 90
      ? "#4ade80"
      : stats.verifiedPercent >= 70
        ? "#facc15"
        : "#f87171";
  const label = !hasData
    ? "No verification data"
    : `${stats.verifiedPercent}% verified (${stats.correctClaims}/${stats.totalClaims} claims)`;

  return (
    <div className="trust-bar fixed bottom-0 left-0 right-0 z-20 px-4 py-2 flex items-center justify-center gap-6 text-xs font-medium"
      style={{ color: "var(--text-secondary)" }}
    >
      <span className="flex items-center gap-1.5">
        <span
          className="inline-block w-2 h-2 rounded-full"
          style={{ background: dotColor }}
        />
        {label}
      </span>
      <span style={{ color: "var(--border)" }}>|</span>
      <span>{groupCount} sections</span>
    </div>
  );
}
