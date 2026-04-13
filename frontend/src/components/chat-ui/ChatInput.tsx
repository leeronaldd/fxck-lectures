"use client";

import { useRef, useEffect, useCallback } from "react";
import { useAppStore } from "@/lib/store";

interface Props {
  onSubmit: () => void;
  placeholder?: string;
  disabled?: boolean;
}

export default function ChatInput({ onSubmit, placeholder = "Drop a lecture transcript or video...", disabled }: Props) {
  const { transcriptFile, videoFile, setTranscriptFile, setVideoFile, isProcessing } = useAppStore();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const file = transcriptFile || videoFile;

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 200)}px`;
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const isVideo = /\.(mp4|mkv|avi|mov|webm|mp3|m4a|wav)$/i.test(f.name);
    if (isVideo) setVideoFile(f);
    else setTranscriptFile(f);
    e.target.value = "";
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (!f) return;
    const isVideo = /\.(mp4|mkv|avi|mov|webm|mp3|m4a|wav)$/i.test(f.name);
    if (isVideo) setVideoFile(f);
    else setTranscriptFile(f);
  }, [setTranscriptFile, setVideoFile]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (file && !disabled) onSubmit();
    }
  };

  const removeFile = () => {
    setTranscriptFile(null);
    setVideoFile(null);
  };

  const isVideo = videoFile != null;
  const canSubmit = !!file && !disabled && !isProcessing;

  return (
    <div className="w-full max-w-3xl mx-auto">
      <div
        className="relative rounded-2xl transition-all"
        style={{
          background: "rgba(255,255,255,0.05)",
          border: "1px solid rgba(255,255,255,0.1)",
          boxShadow: "0 0 0 1px rgba(255,255,255,0.03)",
        }}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        {/* File attachment preview */}
        {file && (
          <div className="flex items-center gap-2 px-4 pt-3">
            <div
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs"
              style={{ background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.1)" }}
            >
              {isVideo ? (
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round">
                  <polygon points="23 7 16 12 23 17 23 7" />
                  <rect x="1" y="5" width="15" height="14" rx="2" />
                </svg>
              ) : (
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
              )}
              <span style={{ color: "var(--text-primary)" }} className="max-w-[200px] truncate">
                {file.name}
              </span>
              <button
                onClick={removeFile}
                className="ml-1 transition-colors"
                style={{ color: "var(--text-muted)" }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-primary)")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-muted)")}
              >
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
          </div>
        )}

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          rows={1}
          placeholder={placeholder}
          onKeyDown={handleKeyDown}
          className="w-full resize-none bg-transparent outline-none px-4 py-3.5 text-sm leading-relaxed"
          style={{
            color: "var(--text-primary)",
            caretColor: "var(--accent)",
            minHeight: "52px",
            maxHeight: "200px",
          }}
          disabled={disabled}
        />

        {/* Bottom toolbar */}
        <div className="flex items-center justify-between px-3 pb-3">
          <div className="flex items-center gap-1">
            {/* File attach */}
            <button
              onClick={() => fileInputRef.current?.click()}
              className="p-2 rounded-xl transition-colors"
              style={{ color: "var(--text-muted)" }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(255,255,255,0.07)";
                e.currentTarget.style.color = "var(--text-secondary)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
                e.currentTarget.style.color = "var(--text-muted)";
              }}
              title="Attach file"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
              </svg>
            </button>

            {/* File type indicator */}
            {file && (
              <span className="text-xs px-2 py-1 rounded-lg" style={{ color: "var(--accent)", background: "var(--accent-dim)" }}>
                {isVideo ? "Video" : "Transcript"}
              </span>
            )}
          </div>

          {/* Send button */}
          <button
            onClick={() => canSubmit && onSubmit()}
            disabled={!canSubmit}
            className="w-8 h-8 rounded-xl flex items-center justify-center transition-all"
            style={{
              background: canSubmit
                ? "linear-gradient(135deg, var(--accent), #FF8555)"
                : "rgba(255,255,255,0.06)",
              color: canSubmit ? "#fff" : "var(--text-muted)",
              boxShadow: canSubmit ? "0 4px 16px var(--accent-glow)" : "none",
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </div>

      <p className="text-center text-xs mt-2" style={{ color: "var(--text-muted)" }}>
        Supports .txt .pdf transcripts and .mp4 .mp3 video/audio
      </p>

      <input
        ref={fileInputRef}
        type="file"
        accept=".txt,.pdf,.mp4,.mkv,.avi,.mov,.webm,.mp3,.m4a,.wav"
        className="hidden"
        onChange={handleFileChange}
      />
    </div>
  );
}
