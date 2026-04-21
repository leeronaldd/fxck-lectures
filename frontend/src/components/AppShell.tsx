"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { createClient } from "@/lib/supabase";
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

  // Avatar dropdown — needed because reader collapses the sidebar, which
  // hides the account menu there. This keeps Settings/Log Out reachable
  // from every page.
  const [avatarMenuOpen, setAvatarMenuOpen] = useState(false);
  const avatarMenuRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!avatarMenuOpen) return;
    const onDown = (e: MouseEvent) => {
      if (avatarMenuRef.current && !avatarMenuRef.current.contains(e.target as Node)) {
        setAvatarMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [avatarMenuOpen]);

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
        className="sticky top-0 z-[100] flex items-center justify-between px-4 sm:px-6 py-2.5 h-[56px] isolate"
        style={{
          background: "rgba(10, 10, 15, 0.7)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          borderBottom: "1px solid var(--border)",
          pointerEvents: "auto",
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
                {usage.used}/{usage.limit} runs used this month
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
            <>
              {/* Dedicated Settings button — always one click away, no dropdown
                  to hunt for. Especially needed on /reader where the sidebar
                  is force-collapsed. */}
              <button
                onClick={() => router.push("/settings")}
                className="p-2 rounded-lg transition-colors"
                style={{ color: "var(--text-secondary)" }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-elevated)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                title="Settings"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="3" />
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
                </svg>
              </button>
            <div ref={avatarMenuRef} className="relative">
              <button
                onClick={() => setAvatarMenuOpen((v) => !v)}
                className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold transition-transform hover:scale-105"
                style={{
                  background: "linear-gradient(135deg, var(--accent), #FF8555)",
                  color: "#fff",
                }}
                title="Account"
              >
                {user.name.charAt(0).toUpperCase()}
              </button>
              {avatarMenuOpen && (
                <div
                  className="absolute right-0 top-full mt-2 w-44 rounded-xl overflow-hidden z-[110]"
                  style={{
                    background: "rgba(20, 20, 25, 0.95)",
                    backdropFilter: "blur(20px)",
                    WebkitBackdropFilter: "blur(20px)",
                    border: "1px solid var(--border)",
                    boxShadow: "0 12px 32px rgba(0, 0, 0, 0.4)",
                  }}
                >
                  <button
                    onClick={() => { setAvatarMenuOpen(false); router.push("/settings"); }}
                    className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-sm text-left transition-colors"
                    style={{ color: "var(--text-primary)" }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-elevated)")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                  >
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="3" />
                      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
                    </svg>
                    Settings
                  </button>
                  <div style={{ borderTop: "1px solid var(--border)" }} />
                  <button
                    onClick={async () => {
                      setAvatarMenuOpen(false);
                      const supabase = createClient();
                      await supabase.auth.signOut();
                    }}
                    className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-sm text-left transition-colors"
                    style={{ color: "var(--text-primary)" }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-elevated)")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                  >
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                      <polyline points="16 17 21 12 16 7" />
                      <line x1="21" y1="12" x2="9" y2="12" />
                    </svg>
                    Log Out
                  </button>
                </div>
              )}
            </div>
            </>
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
