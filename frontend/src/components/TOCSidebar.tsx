"use client";

import { ConceptGroup } from "@/lib/types";
import { getCIColor } from "@/lib/data";

interface TOCSidebarProps {
  groups: ConceptGroup[];
  activeSection: string;
  isOpen: boolean;
  onToggle: () => void;
}

// Match rehype-slug: & becomes -- not -
function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/&/g, "-")
    .replace(/[^a-z0-9-]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

export default function TOCSidebar({
  groups,
  activeSection,
  isOpen,
  onToggle,
}: TOCSidebarProps) {
  const handleClick = (groupName: string) => {
    const slug = slugify(groupName);
    const el = document.getElementById(slug);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  return (
    <>
      {/* Mobile toggle — positioned below AppShell top bar */}
      <button
        onClick={onToggle}
        className="fixed top-[56px] left-3 z-40 lg:hidden rounded-lg p-2 hover:bg-[var(--bg-surface)] transition-colors"
        style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}
        aria-label="Toggle table of contents"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M2 4h12M2 8h12M2 12h12" />
        </svg>
      </button>

      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={onToggle}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed top-[49px] left-0 h-[calc(100vh-49px)] w-[260px] z-30
          bg-[var(--bg-primary)] border-r border-[var(--border)]
          overflow-y-auto shrink-0
          transition-transform duration-200
          lg:sticky lg:top-0 lg:translate-x-0 lg:z-auto
          ${isOpen ? "translate-x-0" : "-translate-x-full"}
        `}
      >
        {/* Header */}
        <div className="sticky top-0 bg-[var(--bg-primary)] border-b border-[var(--border)] px-4 py-4">
          <h2
            className="text-sm font-semibold uppercase tracking-wider"
            style={{ color: "var(--text-secondary)" }}
          >
            Contents
          </h2>
        </div>

        {/* Groups */}
        <nav className="py-2">
          {groups.map((group) => {
            const slug = slugify(group.group_name);
            const isActive = activeSection === slug;
            const isSkipped = group.action === "skip";

            return (
              <button
                key={group.group_index}
                onClick={() => handleClick(group.group_name)}
                className={`
                  toc-item w-full text-left px-4 py-2.5
                  border-l-2 border-transparent
                  hover:bg-[var(--accent-dim)]
                  ${isActive ? "active" : ""}
                  ${isSkipped ? "opacity-50" : ""}
                `}
              >
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={`text-sm leading-tight ${
                      isSkipped
                        ? "line-through text-[var(--text-muted)]"
                        : "text-[var(--text-primary)]"
                    } ${isActive ? "font-medium" : ""}`}
                  >
                    {group.group_name}
                  </span>
                  {group.ci_percent > 0 && (
                    <span
                      className="shrink-0 text-[11px] font-semibold px-1.5 py-0.5 rounded-full"
                      style={{
                        background: `${getCIColor(group.ci_percent)}22`,
                        color: getCIColor(group.ci_percent),
                      }}
                    >
                      {group.ci_percent}%
                    </span>
                  )}
                </div>
                {isSkipped && group.skip_message && (
                  <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                    {group.skip_message}
                  </p>
                )}
              </button>
            );
          })}
        </nav>
      </aside>
    </>
  );
}
