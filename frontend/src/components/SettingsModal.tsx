"use client";

import { AppSettings } from "@/lib/store";

interface SettingsModalProps {
  settings: AppSettings;
  onUpdate: (partial: Partial<AppSettings>) => void;
  onClose: () => void;
}

export default function SettingsModal({ settings, onUpdate, onClose }: SettingsModalProps) {
  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40" style={{ background: "rgba(0, 0, 0, 0.7)" }} onClick={onClose} />

      {/* Modal */}
      <div
        className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-sm rounded-xl p-6"
        style={{
          background: "rgb(18, 18, 22)",
          border: "1px solid var(--border)",
          boxShadow: "0 24px 48px rgba(0, 0, 0, 0.5)",
        }}
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
            Settings
          </h2>
          <button
            onClick={onClose}
            className="text-sm px-3 py-1.5 rounded-lg"
            style={{ color: "var(--accent)", background: "var(--accent-dim)" }}
          >
            Done
          </button>
        </div>

        {/* Model */}
        <div>
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
      </div>
    </>
  );
}
