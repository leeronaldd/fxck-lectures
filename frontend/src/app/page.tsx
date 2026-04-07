"use client";

import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";
import UploadZone from "@/components/UploadZone";

export default function UploadPage() {
  const router = useRouter();

  const {
    transcriptFile,
    videoFile,
    setTranscriptFile,
    setVideoFile,
    startPipeline,
  } = useAppStore();

  const handleGenerate = () => {
    startPipeline();
    router.push("/processing");
  };

  return (
    <div className="flex-1 flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-lg">
        {/* Heading */}
        <div className="text-center mb-8">
          <h1
            className="text-3xl font-bold mb-2"
            style={{ color: "var(--text-primary)", fontFamily: "system-ui, sans-serif" }}
          >
            Fxck Lectures
          </h1>
          <p className="text-base" style={{ color: "var(--text-secondary)" }}>
            Replace a 2 hour lecture with a 15 minute read
          </p>
        </div>

        {/* Upload zone */}
        <UploadZone
          videoFile={videoFile}
          transcriptFile={transcriptFile}
          onVideoChange={setVideoFile}
          onTranscriptChange={setTranscriptFile}
        />

        {/* Generate button */}
        <button
          onClick={handleGenerate}
          disabled={!transcriptFile && !videoFile}
          className="w-full mt-6 py-3 px-6 rounded-xl text-sm font-semibold transition-all disabled:opacity-30 disabled:cursor-not-allowed"
          style={{
            background: transcriptFile || videoFile ? "var(--accent)" : "var(--bg-elevated)",
            color: transcriptFile || videoFile ? "#fff" : "var(--text-muted)",
          }}
        >
          Transform Lecture
        </button>
      </div>
    </div>
  );
}
