"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";
import UploadZone from "@/components/UploadZone";

export default function UploadPage() {
  const router = useRouter();

  const {
    user,
    transcriptFile,
    videoFile,
    slidesFile,
    setTranscriptFile,
    setVideoFile,
    setSlidesFile,
    startPipeline,
    uploadProgress,
    isUploading,
    pipelineRuns,
  } = useAppStore();

  // If there's an active pipeline run (upload or processing), send the user back to it
  // so navigating away doesn't make it look like the upload stopped
  useEffect(() => {
    const activeRun = Object.values(pipelineRuns).find((r) => r.isProcessing);
    if (activeRun) {
      router.replace(`/processing?id=${activeRun.fileId}`);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleGenerate = () => {
    startPipeline();
    router.push("/processing");
  };

  const hasFile = transcriptFile || videoFile;

  return (
    <div className="flex-1 relative overflow-hidden overflow-y-auto">
      {/* Background effects */}
      <div className="hero-glow hero-glow-pulse" />

      {/* Content */}
      <div className="relative z-10 max-w-lg mx-auto px-4 sm:px-6 pt-10 sm:pt-16 pb-16">
        {/* Greeting */}
        <div className="text-center mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold mb-2" style={{ color: "var(--text-primary)" }}>
            {user.isLoggedIn ? `Welcome back, ${user.name.split(" ")[0]}` : "Transform a lecture"}
          </h1>
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
            Drop your lecture recording or transcript and we'll rewrite it as a tutor-quality read.
          </p>
        </div>

        {/* Upload card */}
        <div className="glass rounded-2xl p-6 sm:p-8">
          <UploadZone
            videoFile={videoFile}
            transcriptFile={transcriptFile}
            slidesFile={slidesFile}
            onVideoChange={setVideoFile}
            onTranscriptChange={setTranscriptFile}
            onSlidesChange={setSlidesFile}
            uploadProgress={uploadProgress}
            isUploading={isUploading}
          />

          {/* Generate button */}
          <button
            onClick={handleGenerate}
            disabled={!hasFile}
            className="btn-glow w-full mt-6 py-3.5 px-6 rounded-xl text-sm font-semibold transition-all disabled:opacity-30 disabled:cursor-not-allowed"
            style={{
              background: hasFile
                ? "linear-gradient(135deg, var(--accent), #FF8555)"
                : "var(--bg-elevated)",
              color: hasFile ? "#fff" : "var(--text-muted)",
              boxShadow: hasFile ? "0 8px 32px var(--accent-glow)" : "none",
            }}
          >
            Transform Lecture
          </button>

          <p className="text-center text-xs mt-4" style={{ color: "var(--text-muted)" }}>
            Supports .mp4/.mp3 lecture recordings and .txt transcripts
          </p>
        </div>

        {/* Recent sessions are shown in the sidebar */}
      </div>
    </div>
  );
}
