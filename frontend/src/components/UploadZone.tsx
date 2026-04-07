"use client";

import { useCallback, useState, useRef } from "react";

interface UploadSlotProps {
  label: string;
  accept: string;
  required?: boolean;
  file: File | null;
  onFileChange: (f: File | null) => void;
  icon: string;
}

function UploadSlot({ label, accept, required, file, onFileChange, icon }: UploadSlotProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const f = e.dataTransfer.files[0];
      if (f) onFileChange(f);
    },
    [onFileChange]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => setIsDragOver(false), []);

  const handleClick = useCallback(() => inputRef.current?.click(), []);

  const handleInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      if (f) onFileChange(f);
    },
    [onFileChange]
  );

  if (file) {
    return (
      <div
        className="rounded-xl border px-4 py-3 flex items-center justify-between gap-3"
        style={{ background: "var(--bg-surface)", borderColor: "var(--border)" }}
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-lg">{icon}</span>
          <div className="min-w-0">
            <p className="text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>
              {file.name}
            </p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              {(file.size / 1024).toFixed(0)} KB
            </p>
          </div>
        </div>
        <button
          onClick={() => onFileChange(null)}
          className="text-xs px-2 py-1 rounded-lg hover:bg-[var(--bg-elevated)] transition-colors"
          style={{ color: "var(--text-secondary)" }}
        >
          Remove
        </button>
      </div>
    );
  }

  return (
    <div
      className={`rounded-xl border-2 border-dashed px-4 py-6 text-center cursor-pointer transition-all ${
        isDragOver ? "scale-[1.02]" : ""
      }`}
      style={{
        borderColor: isDragOver ? "var(--accent)" : "var(--border)",
        background: isDragOver ? "var(--accent-dim)" : "transparent",
      }}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={handleClick}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={handleInput}
      />
      <span className="text-2xl block mb-1">{icon}</span>
      <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
        {label}
      </p>
      <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
        {accept}
      </p>
    </div>
  );
}

interface UploadZoneProps {
  videoFile: File | null;
  transcriptFile: File | null;
  onVideoChange: (f: File | null) => void;
  onTranscriptChange: (f: File | null) => void;
}

export default function UploadZone({
  videoFile,
  transcriptFile,
  onVideoChange,
  onTranscriptChange,
}: UploadZoneProps) {
  return (
    <div className="space-y-4">
      {/* Primary: Lecture video */}
      <UploadSlot
        label="Drop your lecture here"
        accept=".mp4"
        file={videoFile}
        onFileChange={onVideoChange}
        icon="🎥"
      />

      {/* Secondary: Transcript */}
      <UploadSlot
        label="Or drop a transcript"
        accept=".txt"
        file={transcriptFile}
        onFileChange={onTranscriptChange}
        icon="📄"
      />
    </div>
  );
}
