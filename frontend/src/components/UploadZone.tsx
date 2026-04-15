"use client";

import { useCallback, useState, useRef } from "react";
import * as Progress from "@radix-ui/react-progress";

interface UploadSlotProps {
  label: string;
  accept: string;
  file: File | null;
  onFileChange: (f: File | null) => void;
  icon: React.ReactNode;
  hint: string;
}

function UploadSlot({ label, accept, file, onFileChange, icon, hint }: UploadSlotProps) {
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

  const formatSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (file) {
    return (
      <div
        className="rounded-xl px-4 py-3.5 flex items-center justify-between gap-3 transition-all animate-fade-in-up"
        style={{
          background: "var(--accent-dim)",
          border: "1px solid rgba(255, 107, 53, 0.2)",
        }}
      >
        <div className="flex items-center gap-3 min-w-0">
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: "rgba(255, 107, 53, 0.15)", color: "var(--accent)" }}
          >
            {icon}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>
              {file.name}
            </p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              {formatSize(file.size)}
            </p>
          </div>
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); onFileChange(null); }}
          className="p-1.5 rounded-lg transition-colors hover:bg-[rgba(255,255,255,0.08)]"
          style={{ color: "var(--text-secondary)" }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <path d="M3 3l8 8M11 3l-8 8" />
          </svg>
        </button>
      </div>
    );
  }

  return (
    <div
      className={`rounded-xl border-2 border-dashed px-4 py-8 text-center cursor-pointer transition-all duration-200 ${
        isDragOver ? "scale-[1.01]" : "hover:border-[rgba(255,255,255,0.15)]"
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
      <input ref={inputRef} type="file" accept={accept} className="hidden" onChange={handleInput} />
      <div
        className="w-10 h-10 rounded-lg flex items-center justify-center mx-auto mb-3 transition-colors"
        style={{
          background: isDragOver ? "rgba(255, 107, 53, 0.15)" : "var(--bg-elevated)",
          color: isDragOver ? "var(--accent)" : "var(--text-secondary)",
        }}
      >
        {icon}
      </div>
      <p className="text-sm font-medium mb-0.5" style={{ color: "var(--text-primary)" }}>{label}</p>
      <p className="text-xs" style={{ color: "var(--text-muted)" }}>{hint}</p>
    </div>
  );
}

interface UploadZoneProps {
  videoFile: File | null;
  transcriptFile: File | null;
  slidesFile: File | null;
  slidesFiles?: File[];
  onVideoChange: (f: File | null) => void;
  onTranscriptChange: (f: File | null) => void;
  onSlidesChange: (f: File | null) => void;
  onSlidesFilesChange?: (files: File[]) => void;
  uploadProgress?: number;
  isUploading?: boolean;
}

export default function UploadZone({
  videoFile,
  transcriptFile,
  slidesFile,
  slidesFiles = [],
  onVideoChange,
  onTranscriptChange,
  onSlidesChange,
  onSlidesFilesChange,
  uploadProgress = 0,
  isUploading = false,
}: UploadZoneProps) {
  return (
    <div className="space-y-3">
      {/* Upload progress bar — shows during file upload */}
      {isUploading && (
        <div className="animate-fade-in-up">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
              Uploading...
            </span>
            <span className="text-xs font-mono" style={{ color: "var(--accent)" }}>
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
      )}

      {/* Upload slots */}
      {!isUploading && (
        <>
          {/* Primary: Lecture recording or transcript */}
          <UploadSlot
            label="Drop your lecture recording or transcript"
            accept=".mp4,.mp3,.txt"
            file={videoFile || transcriptFile}
            onFileChange={(f) => {
              if (!f) {
                onVideoChange(null);
                onTranscriptChange(null);
                return;
              }
              const ext = f.name.split(".").pop()?.toLowerCase();
              if (ext === "txt") {
                onTranscriptChange(f);
                onVideoChange(null);
              } else {
                onVideoChange(f);
                onTranscriptChange(null);
              }
            }}
            hint="MP4 video, MP3 audio, or plain text file"
            icon={
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="23,7 16,12 23,17" />
                <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
              </svg>
            }
          />

          {/* Optional: Lecture slides — always visible */}
          <div className="flex items-center gap-3 py-1">
            <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
            <span className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>optional</span>
            <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
          </div>
          {/* Multi-file slides upload — supports split slide decks */}
          {slidesFiles.length > 0 ? (
            <div
              className="rounded-xl border p-4"
              style={{ background: "var(--bg-surface)", borderColor: "var(--border)" }}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                  {slidesFiles.length} slide file{slidesFiles.length > 1 ? "s" : ""}
                </span>
                <button
                  onClick={() => onSlidesFilesChange?.([])}
                  className="text-xs px-2 py-1 rounded-md"
                  style={{ color: "var(--text-muted)" }}
                >
                  Clear
                </button>
              </div>
              {slidesFiles.map((f, i) => (
                <div key={i} className="flex items-center gap-2 text-xs py-1" style={{ color: "var(--text-secondary)" }}>
                  <span>📄</span>
                  <span className="truncate">{f.name}</span>
                  <span style={{ color: "var(--text-muted)" }}>
                    {f.size < 1024 * 1024 ? `${(f.size / 1024).toFixed(0)} KB` : `${(f.size / (1024 * 1024)).toFixed(1)} MB`}
                  </span>
                </div>
              ))}
              <label
                className="flex items-center gap-1.5 mt-2 text-xs cursor-pointer"
                style={{ color: "var(--accent)" }}
              >
                <input
                  type="file"
                  accept=".pdf"
                  multiple
                  className="hidden"
                  onChange={(e) => {
                    const newFiles = Array.from(e.target.files || []);
                    if (newFiles.length > 0) {
                      onSlidesFilesChange?.([...slidesFiles, ...newFiles]);
                    }
                    e.target.value = "";
                  }}
                />
                + Add more slides
              </label>
            </div>
          ) : (
            <UploadSlot
              label="Add lecture slides"
              accept=".pdf"
              file={null}
              onFileChange={(f) => {
                if (f) onSlidesFilesChange?.([f]);
              }}
              hint="PDF — supports multiple files"
              icon={
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="2" y="3" width="20" height="14" rx="2" />
                  <path d="M8 21h8M12 17v4" />
                </svg>
              }
            />
          )}
        </>
      )}
    </div>
  );
}
