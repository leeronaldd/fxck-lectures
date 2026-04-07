"use client";

import { useState, useEffect } from "react";
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
  const store = useAppStore();

  const [markdown, setMarkdown] = useState<string>("");
  const [groups, setGroups] = useState<ConceptGroup[]>([]);
  const [trustStats, setTrustStats] = useState<TrustStats>({
    totalClaims: 0,
    correctClaims: 0,
    verifiedPercent: 0,
  });
  const [loading, setLoading] = useState(true);

  // Auto-collapse app sidebar on reader page
  useEffect(() => {
    store.setSidebarOpen(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load data — from store if available, fallback to static files
  useEffect(() => {
    async function load() {
      if (store.markdown && store.groups.length > 0) {
        setMarkdown(store.markdown);
        setGroups(store.groups);
        setTrustStats(store.trustStats);
      } else {
        const [md, grps, claims] = await Promise.all([
          getMarkdownContent(),
          getConceptGroups(),
          getVerificationReport(),
        ]);
        setMarkdown(md);
        setGroups(grps);
        setTrustStats(computeTrustStats(claims));
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

  return (
    <div className="flex flex-1 overflow-x-hidden">
      {/* Document */}
      <div className="flex-1 min-w-0 overflow-x-hidden">
        <div className="max-w-[720px] mx-auto px-6 lg:px-12 py-8 pb-16 overflow-hidden">
          <MarkdownRenderer content={markdown} />
        </div>
      </div>

      {/* Trust bar */}
      <TrustBar stats={trustStats} groupCount={groups.filter((g) => g.action !== "skip").length} />
    </div>
  );
}
