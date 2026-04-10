"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useAppStore } from "@/lib/store";
import { createClient } from "@/lib/supabase";

export default function AppSidebar() {
  const router = useRouter();
  const { user, sessions, sidebarOpen, settings, updateSettings, loadSession, deleteSession } = useAppStore();
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [renaming, setRenaming] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  if (!sidebarOpen) return null;

  return (
    <>
      {/* Mobile backdrop */}
      <div
        className="fixed inset-0 z-30 lg:hidden"
        style={{ background: "rgba(0, 0, 0, 0.6)", backdropFilter: "blur(4px)" }}
        onClick={() => useAppStore.getState().setSidebarOpen(false)}
      />

      {/* Sidebar */}
      <aside
        className="fixed top-[56px] left-0 bottom-0 w-[280px] z-30 flex flex-col
          lg:sticky lg:top-[56px] lg:h-[calc(100vh-56px)] lg:z-auto lg:shrink-0"
        style={{
          background: "rgba(10, 10, 15, 0.95)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          borderRight: "1px solid var(--border)",
        }}
      >
        {/* New Session button */}
        <div className="p-3">
          <button
            onClick={() => {
              router.push("/upload");
              setTimeout(() => useAppStore.getState().reset(), 100);
            }}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl text-sm font-medium transition-all"
            style={{
              background: "var(--accent-dim)",
              color: "var(--accent)",
              border: "1px solid rgba(255, 107, 53, 0.15)",
            }}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
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
          {sessions.length === 0 ? (
            <p className="px-3 py-4 text-xs" style={{ color: "var(--text-muted)" }}>
              No sessions yet. Upload a lecture to get started.
            </p>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                className="flex items-center rounded-xl mb-0.5 transition-all group"
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "var(--bg-elevated)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "transparent";
                }}
              >
                {renaming === session.id ? (
                  <form
                    className="flex-1 px-3 py-2 min-w-0"
                    onSubmit={async (e) => {
                      e.preventDefault();
                      if (renameValue.trim()) {
                        const { renameSession: apiRename } = await import("@/lib/api");
                        const ok = await apiRename(session.id, renameValue.trim());
                        if (ok) {
                          useAppStore.getState().loadSessions();
                        }
                      }
                      setRenaming(null);
                    }}
                  >
                    <input
                      autoFocus
                      value={renameValue}
                      onChange={(e) => setRenameValue(e.target.value)}
                      onBlur={() => setRenaming(null)}
                      onKeyDown={(e) => { if (e.key === "Escape") setRenaming(null); }}
                      className="w-full text-sm px-2 py-1 rounded-lg outline-none"
                      style={{
                        background: "var(--bg-base)",
                        border: "1px solid var(--accent)",
                        color: "var(--text-primary)",
                      }}
                    />
                  </form>
                ) : (
                  <button
                    onClick={async () => {
                      await loadSession(session.id);
                      router.push("/reader");
                    }}
                    onDoubleClick={(e) => {
                      e.preventDefault();
                      setRenaming(session.id);
                      setRenameValue(session.name);
                    }}
                    className="flex-1 text-left px-3 py-2.5 min-w-0"
                  >
                    <p className="text-sm truncate" style={{ color: "var(--text-primary)" }}>
                      {session.name}
                    </p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                      {session.date}
                    </p>
                  </button>
                )}
                {deleteConfirm === session.id ? (
                  <div className="flex items-center gap-1 mr-1" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={async () => {
                        await deleteSession(session.id);
                        setDeleteConfirm(null);
                      }}
                      className="text-[10px] px-2 py-1 rounded font-medium"
                      style={{ background: "rgba(239,68,68,0.15)", color: "#ef4444" }}
                    >
                      Delete
                    </button>
                    <button
                      onClick={() => setDeleteConfirm(null)}
                      className="text-[10px] px-2 py-1 rounded"
                      style={{ color: "var(--text-muted)" }}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                    {/* Rename */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setRenaming(session.id);
                        setRenameValue(session.name);
                      }}
                      className="p-1.5 rounded-lg"
                      style={{ color: "var(--text-muted)" }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = "var(--accent)")}
                      onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-muted)")}
                      title="Rename"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M17 3a2.828 2.828 0 114 4L7.5 20.5 2 22l1.5-5.5L17 3z" />
                      </svg>
                    </button>
                    {/* Delete */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteConfirm(session.id);
                      }}
                      className="p-1.5 mr-1 rounded-lg"
                      style={{ color: "var(--text-muted)" }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = "#ef4444")}
                      onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-muted)")}
                      title="Delete"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14" />
                      </svg>
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {/* Account section */}
        <div className="relative p-2" style={{ borderTop: "1px solid var(--border)" }}>
          {/* Account menu dropdown */}
          {accountMenuOpen && (
            <div
              className="absolute bottom-full left-2 right-2 mb-1 rounded-xl overflow-hidden"
              style={{
                background: "rgba(20, 20, 25, 0.95)",
                backdropFilter: "blur(20px)",
                border: "1px solid var(--border)",
                boxShadow: "0 -8px 32px rgba(0, 0, 0, 0.3)",
              }}
            >
              {user.isLoggedIn ? (
                <>
                  <MenuItem label="Settings" icon="gear" onClick={() => { setAccountMenuOpen(false); router.push("/settings"); }} />
                  <MenuItem label="Upgrade Plan" icon="star" onClick={() => { setAccountMenuOpen(false); router.push("/settings?tab=Billing"); }} />
                  <div style={{ borderTop: "1px solid var(--border)" }} />
                  <MenuItem
                    label="Log Out"
                    icon="logout"
                    onClick={async () => {
                      const supabase = createClient();
                      await supabase.auth.signOut();
                      setAccountMenuOpen(false);
                    }}
                  />
                </>
              ) : (
                <>
                  <MenuItem label="Settings" icon="gear" onClick={() => { setAccountMenuOpen(false); router.push("/settings"); }} />
                  <div style={{ borderTop: "1px solid var(--border)" }} />
                  <MenuItem
                    label="Sign In"
                    icon="login"
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
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all"
            onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-elevated)")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
          >
            {/* Avatar */}
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold shrink-0"
              style={{
                background: user.isLoggedIn
                  ? "linear-gradient(135deg, var(--accent), #FF8555)"
                  : "var(--bg-elevated)",
                color: user.isLoggedIn ? "#fff" : "var(--text-muted)",
              }}
            >
              {user.isLoggedIn ? user.name.charAt(0).toUpperCase() : "?"}
            </div>
            <div className="min-w-0 text-left">
              <p className="text-sm truncate" style={{ color: "var(--text-primary)" }}>
                {user.isLoggedIn ? user.name : "Guest"}
              </p>
              {user.isLoggedIn && (
                <p className="text-xs truncate" style={{ color: "var(--text-muted)" }}>
                  {user.email}
                </p>
              )}
            </div>
            {/* Chevron */}
            <svg
              width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5"
              className="ml-auto shrink-0"
              style={{ color: "var(--text-muted)", transform: accountMenuOpen ? "rotate(180deg)" : "none", transition: "transform 0.2s" }}
            >
              <path d="M4 6l3 3 3-3" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      </aside>

    </>
  );
}

function MenuItem({ label, icon, onClick }: { label: string; icon: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-3 py-2.5 text-sm transition-all flex items-center gap-2.5"
      style={{ color: "var(--text-primary)" }}
      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-elevated)")}
      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
    >
      <span className="w-4 h-4 flex items-center justify-center" style={{ color: "var(--text-muted)" }}>
        {icon === "gear" && (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
        )}
        {icon === "info" && (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
        )}
        {icon === "star" && (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26"/></svg>
        )}
        {icon === "logout" && (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16,17 21,12 16,7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        )}
        {icon === "login" && (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10,17 15,12 10,7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>
        )}
      </span>
      {label}
    </button>
  );
}
