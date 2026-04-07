"use client";

import { AppSettings } from "@/lib/store";

interface SettingsModalProps {
  settings: AppSettings;
  onUpdate: (partial: Partial<AppSettings>) => void;
  onClose: () => void;
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-center justify-between py-2 cursor-pointer">
      <span className="text-sm" style={{ color: "var(--text-primary)" }}>
        {label}
      </span>
      <button
        onClick={() => onChange(!checked)}
        className="relative w-10 h-5 rounded-full transition-colors"
        style={{
          background: checked ? "var(--accent)" : "var(--bg-elevated)",
        }}
      >
        <span
          className="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform"
          style={{
            transform: checked ? "translateX(22px)" : "translateX(2px)",
          }}
        />
      </button>
    </label>
  );
}

export default function SettingsModal({ settings, onUpdate, onClose }: SettingsModalProps) {
  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/60 z-40" onClick={onClose} />

      {/* Modal */}
      <div
        className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md rounded-xl border p-6"
        style={{ background: "var(--bg-surface)", borderColor: "var(--border)" }}
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
            Settings
          </h2>
          <button
            onClick={onClose}
            className="text-sm px-2 py-1 rounded hover:bg-[var(--bg-elevated)]"
            style={{ color: "var(--text-secondary)" }}
          >
            Done
          </button>
        </div>

        {/* Model */}
        <div className="mb-5">
          <label className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: "var(--text-secondary)" }}>
            Model
          </label>
          <select
            value={settings.model}
            onChange={(e) => onUpdate({ model: e.target.value })}
            className="w-full px-3 py-2 rounded-lg border text-sm outline-none"
            style={{
              background: "var(--bg-elevated)",
              borderColor: "var(--border)",
              color: "var(--text-primary)",
            }}
          >
            <option value="gemini-3.1-pro">Gemini 3.1 Pro</option>
          </select>
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            Generation model for explanations
          </p>
        </div>

        {/* Pipeline toggles */}
        <div className="mb-5">
          <label className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: "var(--text-secondary)" }}>
            Pipeline Options
          </label>
          <div
            className="rounded-lg border px-3 divide-y"
            style={{ borderColor: "var(--border)", divideColor: "var(--border)" }}
          >
            <Toggle
              label="CI% Scoring"
              checked={!settings.skipCI}
              onChange={(v) => onUpdate({ skipCI: !v })}
            />
            <Toggle
              label="Source Verification"
              checked={!settings.skipVerify}
              onChange={(v) => onUpdate({ skipVerify: !v })}
            />
            <Toggle
              label="Completeness Check"
              checked={!settings.skipCompleteness}
              onChange={(v) => onUpdate({ skipCompleteness: !v })}
            />
            <Toggle
              label="Slide Insertion"
              checked={!settings.skipSlides}
              onChange={(v) => onUpdate({ skipSlides: !v })}
            />
          </div>
        </div>

        {/* Grouping mode */}
        <div>
          <label className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: "var(--text-secondary)" }}>
            Concept Grouping
          </label>
          <div className="space-y-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                checked={!settings.llmGrouping}
                onChange={() => onUpdate({ llmGrouping: false })}
                className="accent-[var(--accent)]"
              />
              <span className="text-sm" style={{ color: "var(--text-primary)" }}>
                Deterministic (faster, cheaper)
              </span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                checked={settings.llmGrouping}
                onChange={() => onUpdate({ llmGrouping: true })}
                className="accent-[var(--accent)]"
              />
              <span className="text-sm" style={{ color: "var(--text-primary)" }}>
                LLM grouping (smarter)
              </span>
            </label>
          </div>
        </div>
      </div>
    </>
  );
}
