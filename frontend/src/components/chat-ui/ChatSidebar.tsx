"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";
import { createClient } from "@/lib/supabase";

interface Props {
  open: boolean;
  onToggle: () => void;
}

function groupByDate(sessions: { id: string; name: string; date: string }[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1);
  const last7 = new Date(today); last7.setDate(last7.getDate() - 7);
  const last30 = new Date(today); last30.setDate(last30.getDate() - 30);

  const groups: Record<string, typeof sessions> = {
    Today: [], Yesterday: [], "Last 7 days": [], "Last 30 days": [], Older: [],
  };

  for (const s of sessions) {
    const d = new Date(s.date);
    if (d >= today) groups["Today"].push(s);
    else if (d >= yesterday) groups["Yesterday"].push(s);
    else if (d >= last7) groups["Last 7 days"].push(s);
    else if (d >= last30) groups["Last 30 days"].push(s);
    else groups["Older"].push(s);
  }
  return groups;
}

export default function ChatSidebar({ open, onToggle }: Props) {
  const router = useRouter();
  const { user, sessions, activeSessionId, loadSessions, loadSession, deleteSession, createNewSession } = useAppStore();
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  useEffect(() => {
    if (user.isLoggedIn) loadSessions();
  }, [user.isLoggedIn]);

  const handleNewChat = async () => {
    useAppStore.getState().reset();
    await createNewSession();
    router.push("/chat");
  };

  const handleSelectSession = async (id: string) => {
    await loadSession(id);
    router.push("/chat");
  };

  const handleSignOut = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    useAppStore.getState().clearUser();
    router.push("/");
  };

  const grouped = groupByDate(sessions);

  if (!open) return null;

  return (
    <div
      className="flex flex-col h-full shrink-0 select-none"
      style={{
        width: "280px",
        background: "#0a0a0a",
        borderRight: "1px solid rgba(255,255,255,0.06)",
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-3" style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
        <div className="flex items-center gap-2.5 min-w-0">
          {/* Avatar */}
          <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
            style={{ background: "linear-gradient(135deg, var(--accent), #FF8555)", color: "#fff" }}>
            {user.name.charAt(0).toUpperCase()}
          </div>
          <span className="text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>
            {user.name}
          </span>
        </div>
        {/* Collapse sidebar */}
        <button
          onClick={onToggle}
          className="p-1.5 rounded-lg transition-colors shrink-0"
          style={{ color: "var(--text-muted)" }}
          onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-primary)")}
          onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-muted)")}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <path d="M9 3v18" />
          </svg>
        </button>
      </div>

      {/* New Chat */}
      <div className="px-2 pt-2">
        <button
          onClick={handleNewChat}
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-colors text-left"
          style={{ color: "var(--text-secondary)" }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "rgba(255,255,255,0.05)";
            e.currentTarget.style.color = "var(--text-primary)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "transparent";
            e.currentTarget.style.color = "var(--text-secondary)";
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
          New Session
        </button>
      </div>

      {/* Sessions list */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-4">
        {Object.entries(grouped).map(([label, items]) => {
          if (items.length === 0) return null;
          return (
            <div key={label}>
              <p className="px-3 mb-1 text-[10px] font-semibold uppercase tracking-widest"
                style={{ color: "var(--text-muted)" }}>
                {label}
              </p>
              {items.map((s) => {
                const isActive = s.id === activeSessionId;
                return (
                  <div
                    key={s.id}
                    className="group relative flex items-center rounded-xl mb-0.5 cursor-pointer"
                    style={{ background: isActive ? "rgba(255,255,255,0.07)" : "transparent" }}
                    onMouseEnter={(e) => {
                      setHoveredId(s.id);
                      if (!isActive) e.currentTarget.style.background = "rgba(255,255,255,0.04)";
                    }}
                    onMouseLeave={(e) => {
                      setHoveredId(null);
                      if (!isActive) e.currentTarget.style.background = "transparent";
                    }}
                    onClick={() => handleSelectSession(s.id)}
                  >
                    <div className="flex items-center gap-2 px-3 py-2 min-w-0 flex-1">
                      <span className="text-xs shrink-0" style={{ color: "var(--text-muted)" }}>#</span>
                      <p className="text-sm truncate" style={{ color: isActive ? "var(--text-primary)" : "var(--text-secondary)" }}>
                        {s.name}
                      </p>
                    </div>

                    {/* Delete button — shows on hover */}
                    {hoveredId === s.id && (
                      <button
                        className="shrink-0 mr-2 p-1 rounded-md transition-colors"
                        style={{ color: "var(--text-muted)" }}
                        onMouseEnter={(e) => { e.stopPropagation(); e.currentTarget.style.color = "#FF4444"; }}
                        onMouseLeave={(e) => { e.stopPropagation(); e.currentTarget.style.color = "var(--text-muted)"; }}
                        onClick={(e) => {
                          e.stopPropagation();
                          if (deleteConfirm === s.id) {
                            deleteSession(s.id);
                            setDeleteConfirm(null);
                          } else {
                            setDeleteConfirm(s.id);
                            setTimeout(() => setDeleteConfirm(null), 3000);
                          }
                        }}
                      >
                        {deleteConfirm === s.id ? (
                          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#FF4444" strokeWidth="2" strokeLinecap="round">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        ) : (
                          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                            <polyline points="3 6 5 6 21 6" />
                            <path d="M19 6l-1 14H6L5 6" />
                            <path d="M10 11v6M14 11v6" />
                            <path d="M9 6V4h6v2" />
                          </svg>
                        )}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          );
        })}

        {sessions.length === 0 && (
          <div className="px-3 py-8 text-center">
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>No sessions yet</p>
          </div>
        )}
      </div>

      {/* Footer — sign out */}
      <div className="px-2 pb-3 pt-2" style={{ borderTop: "1px solid rgba(255,255,255,0.04)" }}>
        <button
          onClick={handleSignOut}
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-colors"
          style={{ color: "var(--text-muted)" }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "rgba(255,255,255,0.04)";
            e.currentTarget.style.color = "var(--text-secondary)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "transparent";
            e.currentTarget.style.color = "var(--text-muted)";
          }}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
          Sign out
        </button>
      </div>
    </div>
  );
}
