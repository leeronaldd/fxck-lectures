"use client";

import { useRouter, usePathname } from "next/navigation";
import { useAppStore } from "@/lib/store";
import AppSidebar from "./AppSidebar";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, toggleSidebar, sidebarOpen, settings, updateSettings } = useAppStore();

  const isSignInPage = pathname === "/signin";
  const isReaderPage = pathname === "/reader";

  // Don't show app shell on sign-in page
  if (isSignInPage) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Top bar */}
      <header
        className="sticky top-0 z-40 flex items-center justify-between px-4 py-2.5 border-b h-[49px]"
        style={{ background: "var(--bg-primary)", borderColor: "var(--border)" }}
      >
        <div className="flex items-center gap-2">
          {/* Hamburger */}
          <button
            onClick={toggleSidebar}
            className="p-1.5 rounded-lg hover:bg-[var(--bg-surface)] transition-colors"
            style={{ color: "var(--text-secondary)" }}
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M3 5h12M3 9h12M3 13h12" />
            </svg>
          </button>

          {/* Logo */}
          <button
            onClick={() => router.push("/")}
            className="text-lg font-bold tracking-tight hover:opacity-80 transition-opacity"
            style={{ color: "var(--accent)" }}
          >
            Klare
          </button>
        </div>

        <div className="flex items-center gap-3">
          {/* Model selector */}
          <select
            value={settings.model}
            onChange={(e) => updateSettings({ model: e.target.value })}
            className="text-xs px-3 py-1.5 rounded-lg border outline-none cursor-pointer"
            style={{
              background: "var(--bg-surface)",
              borderColor: "var(--border)",
              color: "var(--text-secondary)",
            }}
          >
            <option value="gemini-3.1-pro">Gemini 3.1 Pro</option>
          </select>

          {/* Sign In button (when logged out) */}
          {!user.isLoggedIn && (
            <button
              onClick={() => router.push("/signin")}
              className="text-xs px-3 py-1.5 rounded-lg border font-medium hover:bg-[var(--bg-surface)] transition-colors"
              style={{ borderColor: "var(--border)", color: "var(--text-primary)" }}
            >
              Sign In
            </button>
          )}
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* App sidebar — hidden on reader page (TOC takes over) */}
        {!isReaderPage && <AppSidebar />}

        {/* Page content */}
        <main className="flex-1 min-w-0 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
