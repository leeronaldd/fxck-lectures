"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAppStore } from "@/lib/store";
import AppSidebar from "./AppSidebar";
import type { UsageInfo } from "@/lib/api";

const PROTECTED_PATHS = ["/upload", "/processing", "/reader", "/chat"];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, authLoading, toggleSidebar, sidebarOpen, settings, updateSettings } = useAppStore();

  const isSignInPage = pathname === "/signin";
  const isReaderPage = pathname === "/reader";
  const isLandingPage = pathname === "/";
  const isQuizPage = pathname === "/quiz";

  // Route protection
  useEffect(() => {
    if (authLoading) return;
    if (user.isLoggedIn && (isSignInPage || isLandingPage)) {
      router.replace("/upload");
      return;
    }
    if (!user.isLoggedIn && PROTECTED_PATHS.includes(pathname)) {
      router.push("/signin");
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user.isLoggedIn, authLoading, pathname, router]);

  // Refresh session list when tab becomes visible (handles cross-device/tab sync)
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === "visible" && user.isLoggedIn) {
        useAppStore.getState().loadSessions();
      }
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [user.isLoggedIn]);

  // Usage pill — small indicator next to avatar, refreshed when a run finishes
  const [usage, setUsage] = useState<UsageInfo | null>(null);
  const { pipelineRuns } = useAppStore();
  const anyDone = Object.values(pipelineRuns).filter((r) => r.isDone).length;
  useEffect(() => {
    if (!user.isLoggedIn) { setUsage(null); return; }
    (async () => {
      try {
        const { fetchUsage } = await import("@/lib/api");
        const u = await fetchUsage();
        if (u) setUsage(u);
      } catch {}
    })();
  }, [user.isLoggedIn, anyDone]);

  // Don't show app shell on sign-in, quiz, preview, or landing page (for guests only)
  const isPreviewPage = pathname === "/preview";
  const isChatPage = pathname.startsWith("/chat");
  if (isSignInPage || isQuizPage || isPreviewPage || isChatPage || (isLandingPage && !user.isLoggedIn)) {
    return <>{children}</>;
  }

  // Show nothing while auth is loading to prevent flash of wrong page
  if (authLoading && PROTECTED_PATHS.includes(pathname)) {
    return (
      <div className="h-screen flex items-center justify-center" style={{ background: "var(--bg-base)" }}>
        <div className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }} />
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Top bar — glassmorphism */}
      <header
        className="sticky top-0 z-40 flex items-center justify-between px-4 sm:px-6 py-2.5 h-[56px]"
        style={{
          background: "rgba(10, 10, 15, 0.7)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div className="flex items-center gap-3">
          {/* Hamburger */}
          <button
            onClick={toggleSidebar}
            className="p-2 rounded-lg transition-colors"
            style={{ color: "var(--text-secondary)" }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-elevated)")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              <path d="M3 5h12M3 9h12M3 13h12" />
            </svg>
          </button>

          {/* Logo — dashboard if logged in, sales page if guest */}
          <button
            onClick={async () => {
              if (user.isLoggedIn) {
                // Don't reset if a pipeline is actively running — just navigate to upload
                const { pipelineRuns, activePipelineId } = useAppStore.getState();
                const isRunning = activePipelineId
                  ? pipelineRuns[activePipelineId]?.isProcessing
                  : Object.values(pipelineRuns).some((r) => r.isProcessing);
                if (!isRunning) {
                  useAppStore.getState().reset();
                  await useAppStore.getState().createNewSession();
                }
                router.push("/upload");
              } else {
                router.push("/");
              }
            }}
            className="transition-opacity hover:opacity-80"
          >
            <img src="/brand/logo-full-dark.svg" alt="Klare" className="h-7" />
          </button>
        </div>

        <div className="flex items-center gap-3">
          {/* Usage pill (logged-in users only, hidden for unlimited whitelist) */}
          {user.isLoggedIn && usage && usage.limit !== -1 && (
            <button
              onClick={() => router.push("/settings?tab=Usage")}
              className="hidden sm:flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-full transition-all"
              style={{
                background:
                  usage.used >= usage.limit
                    ? "rgba(255, 68, 68, 0.12)"
                    : "var(--accent-dim)",
                color: usage.used >= usage.limit ? "#FF6666" : "var(--accent)",
                border: `1px solid ${
                  usage.used >= usage.limit
                    ? "rgba(255, 68, 68, 0.3)"
                    : "rgba(255, 107, 53, 0.25)"
                }`,
              }}
              title={
                usage.used >= usage.limit
                  ? "You've used all your lectures — upgrade for more"
                  : `${usage.limit - usage.used} lecture${usage.limit - usage.used === 1 ? "" : "s"} remaining`
              }
            >
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: "currentColor" }} />
              <span>
                {usage.used}/{usage.limit} runs
              </span>
            </button>
          )}

          {/* Sign In / Avatar */}
          {!user.isLoggedIn ? (
            <button
              onClick={() => router.push("/signin")}
              className="text-xs px-4 py-2 rounded-lg font-medium transition-all"
              style={{
                background: "var(--accent-dim)",
                color: "var(--accent)",
                border: "1px solid rgba(255, 107, 53, 0.2)",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(255, 107, 53, 0.2)";
                e.currentTarget.style.borderColor = "rgba(255, 107, 53, 0.3)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "var(--accent-dim)";
                e.currentTarget.style.borderColor = "rgba(255, 107, 53, 0.2)";
              }}
            >
              Sign In
            </button>
          ) : (
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold"
              style={{
                background: "linear-gradient(135deg, var(--accent), #FF8555)",
                color: "#fff",
              }}
            >
              {user.name.charAt(0).toUpperCase()}
            </div>
          )}
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        <AppSidebar />
        <main className="flex-1 min-w-0 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
