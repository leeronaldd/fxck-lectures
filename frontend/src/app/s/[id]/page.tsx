"use client";

// Public share viewer — /s/[id] — the viral loop landing page. Anyone with
// the link can read the doc without signing in. Every shared doc ends with
// a "Make your own" CTA that converts classmates into new users.
//
// Security: session IDs are unguessable UUIDs, so this is safe as "anyone
// with link" sharing. The backend /api/public/session endpoint returns
// only id/name/markdown/created_at — no user metadata leaked.

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { fetchPublicSession } from "@/lib/api";
import { SlideCardGroup } from "@/components/SlideCard";
import NarrativeSection from "@/components/NarrativeSection";
import ImageLightbox from "@/components/ImageLightbox";
import type { SlideCard, TranscriptSection } from "@/lib/types";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function PublicSharePage({ params }: PageProps) {
  const { id } = use(params);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sessionName, setSessionName] = useState("");
  const [slides, setSlides] = useState<SlideCard[]>([]);
  const [transcript, setTranscript] = useState<TranscriptSection[]>([]);
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      let data: Awaited<ReturnType<typeof fetchPublicSession>> = null;
      try {
        data = await fetchPublicSession(id);
      } catch {
        // Network/CORS error — treat the same as 404 so the page exits
        // loading state instead of hanging.
        data = null;
      }
      if (cancelled) return;
      if (!data) {
        setError("This document doesn't exist or has been removed.");
        setLoading(false);
        return;
      }
      setSessionName(data.name || "Untitled lecture");

      // markdown is a JSON string with {slides, transcript} for V2 sessions.
      if (data.markdown && data.markdown.trim().startsWith("{")) {
        try {
          const parsed = JSON.parse(data.markdown);
          setSlides((parsed.slides || []).filter(Boolean));
          setTranscript((parsed.transcript || []).filter(Boolean));
        } catch {
          setError("This document couldn't be loaded.");
        }
      } else {
        // Legacy markdown — treat the whole thing as one narrative section
        setTranscript([
          {
            slide_number: 1,
            title: data.name || "Notes",
            narrative: data.markdown || "",
            ei_percent: 0,
            ei_reasoning: "",
          },
        ]);
      }
      setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center" style={{ background: "var(--bg-base)" }}>
        <div
          className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin"
          style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}
        />
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="min-h-screen flex flex-col items-center justify-center px-6 text-center"
        style={{ background: "var(--bg-base)", color: "var(--text-primary)" }}
      >
        <h1 className="text-2xl font-bold mb-3">Document not found</h1>
        <p className="text-sm mb-8" style={{ color: "var(--text-muted)" }}>
          {error}
        </p>
        <Link
          href="/"
          className="px-5 py-2.5 rounded-xl text-sm font-semibold"
          style={{
            background: "linear-gradient(135deg, var(--accent), #FF8555)",
            color: "#fff",
          }}
        >
          Go to Klare
        </Link>
      </div>
    );
  }

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--bg-base)" }}
    >
      {/* Minimal top bar — just the logo */}
      <header
        className="flex items-center justify-between px-6 py-4 border-b"
        style={{ borderColor: "var(--border)" }}
      >
        <Link href="/" className="flex items-center gap-2">
          <img src="/brand/logo-full-dark.svg" alt="Klare" className="h-6" />
        </Link>
        <Link
          href="/signin"
          className="text-xs px-4 py-2 rounded-lg font-medium transition-all"
          style={{
            background: "var(--accent-dim)",
            color: "var(--accent)",
            border: "1px solid rgba(255, 107, 53, 0.2)",
          }}
        >
          Make your own
        </Link>
      </header>

      {/* Main content — single-column for mobile-first readability */}
      <main className="flex-1 max-w-3xl mx-auto w-full px-4 sm:px-6 py-8 sm:py-12">
        <h1
          className="text-3xl sm:text-4xl font-bold mb-2"
          style={{ color: "var(--text-primary)" }}
        >
          {sessionName}
        </h1>
        <p className="text-xs mb-8" style={{ color: "var(--text-muted)" }}>
          Shared via Klare · re-taught from the original lecture
        </p>

        {transcript.map((section, i) => {
          const sectionSlides = slides.filter(
            (s) =>
              parseInt(s.slide_id?.replace(/\D/g, "") || "0") ===
              section.slide_number
          );
          return (
            <div key={i} className="mb-12">
              {sectionSlides.length > 0 && (
                <div className="mb-6">
                  <SlideCardGroup
                    cards={sectionSlides}
                    onImageClick={setLightboxSrc}
                  />
                </div>
              )}
              <NarrativeSection section={section} />
              {i < transcript.length - 1 && (
                <hr
                  className="mt-12"
                  style={{ borderColor: "var(--border)" }}
                />
              )}
            </div>
          );
        })}

        {/* Viral-loop CTA at the bottom */}
        <div
          className="mt-16 rounded-2xl p-8 text-center"
          style={{
            background:
              "linear-gradient(135deg, rgba(255,107,53,0.1), rgba(139,92,246,0.08))",
            border: "1px solid rgba(255,107,53,0.18)",
          }}
        >
          <h2
            className="text-xl sm:text-2xl font-bold mb-3"
            style={{ color: "var(--text-primary)" }}
          >
            Got a lecture that sucks?
          </h2>
          <p
            className="text-sm mb-6 max-w-md mx-auto"
            style={{ color: "var(--text-secondary)" }}
          >
            Klare re-teaches bad professors&apos; lectures from scratch.
            Upload your own and get a 20-minute read that actually makes
            sense.
          </p>
          <Link
            href="/"
            className="inline-block px-8 py-3 rounded-xl text-sm font-semibold transition-transform hover:scale-105"
            style={{
              background: "linear-gradient(135deg, var(--accent), #FF8555)",
              color: "#fff",
              boxShadow: "0 8px 32px var(--accent-glow)",
            }}
          >
            Try Klare free
          </Link>
          <p className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
            Free · no card required
          </p>
        </div>
      </main>

      {/* Footer attribution */}
      <footer
        className="text-center py-6 text-xs"
        style={{ color: "var(--text-muted)" }}
      >
        Made with{" "}
        <Link
          href="/"
          style={{ color: "var(--accent)" }}
          className="hover:underline"
        >
          Klare
        </Link>{" "}
        · klareai.com
      </footer>

      {lightboxSrc && (
        <ImageLightbox src={lightboxSrc} onClose={() => setLightboxSrc(null)} />
      )}
    </div>
  );
}
