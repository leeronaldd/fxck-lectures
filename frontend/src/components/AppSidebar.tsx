"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";

export default function AppSidebar() {
  const router = useRouter();
  const { user, sessions, signOut, sidebarOpen } = useAppStore();
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);

  if (!sidebarOpen) return null;

  return (
    <>
      {/* Mobile backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-30 lg:hidden"
        onClick={() => useAppStore.getState().setSidebarOpen(false)}
      />

      {/* Sidebar */}
      <aside
        className="fixed top-[49px] left-0 bottom-0 w-[280px] z-30 flex flex-col
          bg-[var(--bg-primary)] border-r border-[var(--border)]
          lg:sticky lg:top-[49px] lg:h-[calc(100vh-49px)] lg:z-auto lg:shrink-0"
      >
        {/* New Session button */}
        <div className="p-3">
          <button
            onClick={() => {
              useAppStore.getState().reset();
              router.push("/");
            }}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors hover:bg-[var(--accent-dim)]"
            style={{ color: "var(--accent)" }}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M8 3v10M3 8h10" />
            </svg>
            New Session
          </button>
        </div>

        {/* Sessions list */}
        <div className="flex-1 overflow-y-auto px-2">
          <p className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-widest"
            style={{ color: "var(--text-muted)" }}>
            Recent
          </p>
          {sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => router.push("/reader")}
              className="w-full text-left px-3 py-2 rounded-lg mb-0.5 hover:bg-[var(--bg-surface)] transition-colors group"
            >
              <p className="text-sm truncate" style={{ color: "var(--text-primary)" }}>
                {session.name}
              </p>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                {session.date}
              </p>
            </button>
          ))}
        </div>

        {/* Account section */}
        <div className="relative border-t border-[var(--border)] p-2">
          {/* Account menu dropdown */}
          {accountMenuOpen && (
            <div
              className="absolute bottom-full left-2 right-2 mb-1 rounded-lg border overflow-hidden"
              style={{ background: "var(--bg-surface)", borderColor: "var(--border)" }}
            >
              {user.isLoggedIn ? (
                <>
                  <MenuItem label="Settings" onClick={() => { setAccountMenuOpen(false); }} />
                  <MenuItem label="Learn More" onClick={() => { setAccountMenuOpen(false); }} />
                  <MenuItem label="Upgrade Plan" onClick={() => { setAccountMenuOpen(false); }} />
                  <div className="border-t border-[var(--border)]" />
                  <MenuItem
                    label="Log Out"
                    onClick={() => {
                      signOut();
                      setAccountMenuOpen(false);
                    }}
                  />
                </>
              ) : (
                <>
                  <MenuItem label="Settings" onClick={() => { setAccountMenuOpen(false); }} />
                  <MenuItem label="Learn More" onClick={() => { setAccountMenuOpen(false); }} />
                  <div className="border-t border-[var(--border)]" />
                  <MenuItem
                    label="Sign In"
                    onClick={() => {
                      setAccountMenuOpen(false);
                      router.push("/signin");
                    }}
                  />
                </>
              )}
            </div>
          )}

          {/* Account button */}
          <button
            onClick={() => setAccountMenuOpen(!accountMenuOpen)}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-[var(--bg-surface)] transition-colors"
          >
            {/* Avatar */}
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold shrink-0"
              style={{
                background: user.isLoggedIn ? "var(--accent)" : "var(--bg-elevated)",
                color: user.isLoggedIn ? "#fff" : "var(--text-muted)",
              }}
            >
              {user.isLoggedIn ? user.name.charAt(0).toUpperCase() : "?"}
            </div>
            <div className="min-w-0 text-left">
              <p className="text-sm truncate" style={{ color: "var(--text-primary)" }}>
                {user.isLoggedIn ? user.name : "Guest Account"}
              </p>
              {user.isLoggedIn && (
                <p className="text-xs truncate" style={{ color: "var(--text-muted)" }}>
                  {user.email}
                </p>
              )}
            </div>
          </button>
        </div>
      </aside>
    </>
  );
}

function MenuItem({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-3 py-2 text-sm hover:bg-[var(--bg-elevated)] transition-colors"
      style={{ color: "var(--text-primary)" }}
    >
      {label}
    </button>
  );
}
