"use client";

import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";
import UploadZone from "@/components/UploadZone";

export default function UploadPage() {
  const router = useRouter();

  const {
    user,
    sessions,
    transcriptFile,
    videoFile,
    slidesFile,
    setTranscriptFile,
    setVideoFile,
    setSlidesFile,
    startPipeline,
    uploadProgress,
    isUploading,
    loadSession,
  } = useAppStore();

  const handleGenerate = () => {
    startPipeline();
    router.push("/processing");
  };

  const hasFile = transcriptFile || videoFile;
  const recentSessions = sessions.slice(0, 5);

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
            Supports .mp4 lecture recordings and .txt transcripts
          </p>
        </div>

        {/* Recent sessions */}
        {recentSessions.length > 0 && (
          <div className="mt-10">
            <h2 className="text-sm font-semibold mb-3" style={{ color: "var(--text-secondary)" }}>
              Recent lectures
            </h2>
            <div className="space-y-2">
              {recentSessions.map((session) => (
                <button
                  key={session.id}
                  onClick={async () => {
                    await loadSession(session.id);
                    router.push("/reader");
                  }}
                  className="w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all text-left"
                  style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)" }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = "rgba(255,107,53,0.3)")}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>
                      {session.name}
                    </p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                      {session.date}
                    </p>
                  </div>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ color: "var(--text-muted)" }}>
                    <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
