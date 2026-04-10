"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import TrustBar from "@/components/TrustBar";
import { useAppStore } from "@/lib/store";
import {
  getMarkdownContent,
  getConceptGroups,
  getVerificationReport,
  computeTrustStats,
} from "@/lib/data";
import { ConceptGroup, TrustStats } from "@/lib/types";

export default function ReaderPage() {
  const router = useRouter();
  const store = useAppStore();

  const [markdown, setMarkdown] = useState<string>("");
  const [groups, setGroups] = useState<ConceptGroup[]>([]);
  const [trustStats, setTrustStats] = useState<TrustStats>({
    totalClaims: 0,
    correctClaims: 0,
    verifiedPercent: 0,
  });
  const [loading, setLoading] = useState(true);

  // Auto-collapse app sidebar on reader page (user can re-open with hamburger)
  useEffect(() => {
    store.setSidebarOpen(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load data — from store if available, fallback to static files
  useEffect(() => {
    async function load() {
      if (store.markdown) {
        setMarkdown(store.markdown);
        setGroups(store.groups);
        setTrustStats(store.trustStats);
      } else {
        // No data in store — show empty state
        setMarkdown("");
      }
      setLoading(false);
    }
    load();
  }, [store.markdown, store.groups, store.trustStats]);


  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[80vh]">
        <div className="flex flex-col items-center gap-4">
          <div
            className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin"
            style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}
          />
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
            Loading lecture...
          </p>
        </div>
      </div>
    );
  }

  if (!markdown) {
    return (
      <div className="flex-1 flex items-center justify-center px-4 py-24">
        <div className="text-center max-w-md">
          <div
            className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6"
            style={{ background: "var(--accent-dim)", color: "var(--accent)" }}
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
              <polyline points="14,2 14,8 20,8" />
            </svg>
          </div>
          <h2 className="text-xl font-bold mb-2" style={{ color: "var(--text-primary)" }}>
            No lecture loaded
          </h2>
          <p className="text-sm mb-6" style={{ color: "var(--text-secondary)" }}>
            Upload a lecture recording or transcript to get started.
          </p>
          <button
            onClick={() => router.push("/")}
            className="btn-glow px-6 py-3 rounded-xl text-sm font-semibold"
            style={{
              background: "linear-gradient(135deg, var(--accent), #FF8555)",
              color: "#fff",
              boxShadow: "0 8px 32px var(--accent-glow)",
            }}
          >
            Upload a Lecture
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 overflow-x-hidden">
      {/* Document */}
      <div className="flex-1 min-w-0 overflow-x-hidden">
        <div className="max-w-[1000px] mx-auto px-6 lg:px-16 py-8 pb-16 overflow-hidden">
          {/* Back to upload */}
          <button
            onClick={() => {
              useAppStore.getState().reset();
              router.push("/upload");
            }}
            className="flex items-center gap-1.5 text-xs mb-6 px-3 py-1.5 rounded-lg transition-colors"
            style={{ color: "var(--text-muted)" }}
            onMouseEnter={(e) => { e.currentTarget.style.color = "var(--accent)"; e.currentTarget.style.background = "var(--accent-dim)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = "var(--text-muted)"; e.currentTarget.style.background = "transparent"; }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 5v14M5 12h14" />
            </svg>
            New Lecture
          </button>
          <MarkdownRenderer content={markdown} />
        </div>
      </div>

      {/* Trust bar */}
      <TrustBar stats={trustStats} groupCount={groups.filter((g) => g.action !== "skip").length} />
    </div>
  );
}
