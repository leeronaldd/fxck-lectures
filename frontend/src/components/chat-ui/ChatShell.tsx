"use client";

import { useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAppStore } from "@/lib/store";
import ChatSidebar from "./ChatSidebar";

export default function ChatShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, authLoading } = useAppStore();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Route protection
  useEffect(() => {
    if (authLoading) return;
    if (!user.isLoggedIn) router.push("/signin");
  }, [user.isLoggedIn, authLoading, router]);

  if (authLoading) {
    return (
      <div className="h-screen flex items-center justify-center" style={{ background: "#000" }}>
        <div className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin"
          style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }} />
      </div>
    );
  }

  return (
    <div className="h-screen flex overflow-hidden" style={{ background: "#000" }}>
      {/* Sidebar */}
      <ChatSidebar open={sidebarOpen} onToggle={() => setSidebarOpen((o) => !o)} />

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        {/* Collapse toggle when sidebar is closed */}
        {!sidebarOpen && (
          <button
            onClick={() => setSidebarOpen(true)}
            className="absolute top-3 left-3 z-10 p-1.5 rounded-lg transition-colors"
            style={{ color: "var(--text-muted)" }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-primary)")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-muted)")}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <path d="M9 3v18" />
            </svg>
          </button>
        )}
        {children}
      </div>
    </div>
  );
}
