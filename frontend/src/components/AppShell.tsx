"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAppStore } from "@/lib/store";
import AppSidebar from "./AppSidebar";

const PROTECTED_PATHS = ["/processing", "/reader"];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, authLoading, toggleSidebar, sidebarOpen, settings, updateSettings } = useAppStore();

  const isSignInPage = pathname === "/signin";
  const isReaderPage = pathname === "/reader";

  // Route protection
  useEffect(() => {
    if (authLoading) return;
    if (user.isLoggedIn && isSignInPage) {
      router.push("/");
      return;
    }
    if (!user.isLoggedIn && PROTECTED_PATHS.includes(pathname)) {
      router.push("/signin");
    }
  }, [user.isLoggedIn, authLoading, pathname, isSignInPage, router]);

  // Don't show app shell on sign-in page
  if (isSignInPage) {
    return <>{children}</>;
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

          {/* Logo */}
          <button
            onClick={() => router.push("/")}
            className="text-lg font-bold tracking-tight transition-opacity hover:opacity-80"
          >
            <span className="gradient-text">Klare</span>
          </button>
        </div>

        <div className="flex items-center gap-3">
          {/* Model selector */}
          <div className="hidden sm:block">
            <select
              value={settings.model}
              onChange={(e) => updateSettings({ model: e.target.value })}
              className="text-xs px-3 py-1.5 rounded-lg outline-none cursor-pointer appearance-none"
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                color: "var(--text-secondary)",
              }}
            >
              <option value="gemini-3.1-pro">Gemini 3.1 Pro</option>
            </select>
          </div>

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
