"use client";

import { useEffect, useState } from "react";

export default function ImageLightbox({ src, onClose }: { src: string; onClose: () => void }) {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);

  // ESC to close
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center cursor-zoom-out"
      style={{ background: "rgba(0, 0, 0, 0.85)", backdropFilter: "blur(8px)" }}
      onClick={onClose}
    >
      <button
        onClick={onClose}
        className="absolute top-4 right-4 w-10 h-10 rounded-full flex items-center justify-center text-white text-xl transition-colors"
        style={{ background: "rgba(255,255,255,0.1)" }}
        onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.2)")}
        onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.1)")}
      >
        &times;
      </button>

      {/* ESC hint */}
      <span className="absolute top-5 left-1/2 -translate-x-1/2 text-xs px-2.5 py-1 rounded-md"
        style={{ background: "rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.4)" }}>
        Press <kbd className="font-mono">ESC</kbd> to close
      </span>

      {/* Loading spinner while image loads */}
      {!loaded && !error && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin"
            style={{ borderColor: "rgba(255,255,255,0.3)", borderTopColor: "transparent" }} />
        </div>
      )}

      {error ? (
        <div className="text-center" onClick={(e) => e.stopPropagation()}>
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4"
            style={{ background: "rgba(255,255,255,0.05)" }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
              <circle cx="8.5" cy="8.5" r="1.5"/>
              <polyline points="21,15 16,10 5,21"/>
            </svg>
          </div>
          <p className="text-sm" style={{ color: "rgba(255,255,255,0.5)" }}>Failed to load image</p>
        </div>
      ) : (
        <img
          src={src}
          alt="Expanded slide"
          className="max-w-[90vw] max-h-[90vh] rounded-2xl shadow-2xl transition-opacity duration-200"
          style={{ objectFit: "contain", background: "white", opacity: loaded ? 1 : 0 }}
          onClick={(e) => e.stopPropagation()}
          onLoad={() => setLoaded(true)}
          onError={() => setError(true)}
        />
      )}
    </div>
  );
}
