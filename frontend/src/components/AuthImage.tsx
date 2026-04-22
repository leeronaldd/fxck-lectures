"use client";

import { useEffect, useState, type CSSProperties } from "react";
import { createClient } from "@/lib/supabase";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, "");

/**
 * Renders an <img> that attaches the Supabase Bearer token when the source
 * points at our own `/api/screenshots/` endpoint. Everything else (GCS
 * signed URLs, data: URIs, same-origin previews) falls through to a plain
 * <img> because those either carry their own auth (signed URL) or don't
 * need any.
 *
 * We do this because `/api/screenshots/` now requires auth — and <img> tags
 * don't attach Authorization headers. The fetch-then-blob dance is the
 * standard workaround that keeps the image rendering flow intact.
 */
function needsAuth(src: string): boolean {
  return Boolean(API_URL) && src.startsWith(`${API_URL}/api/screenshots/`);
}

export default function AuthImage({
  src,
  alt,
  style,
  className,
  loading,
  onClick,
  onLoad,
  onError,
}: {
  src: string;
  alt: string;
  style?: CSSProperties;
  className?: string;
  loading?: "lazy" | "eager";
  onClick?: () => void;
  onLoad?: () => void;
  onError?: () => void;
}) {
  const [resolvedSrc, setResolvedSrc] = useState<string | null>(
    needsAuth(src) ? null : src
  );

  useEffect(() => {
    if (!src) {
      setResolvedSrc(null);
      return;
    }
    if (!needsAuth(src)) {
      setResolvedSrc(src);
      return;
    }

    let cancelled = false;
    let objectUrl: string | null = null;

    (async () => {
      try {
        const supabase = createClient();
        const {
          data: { session },
        } = await supabase.auth.getSession();
        const token = session?.access_token;
        if (!token) {
          if (!cancelled) onError?.();
          return;
        }
        const res = await fetch(src, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) {
          if (!cancelled) onError?.();
          return;
        }
        const blob = await res.blob();
        objectUrl = URL.createObjectURL(blob);
        if (!cancelled) setResolvedSrc(objectUrl);
      } catch {
        if (!cancelled) onError?.();
      }
    })();

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [src, onError]);

  if (!resolvedSrc) {
    return (
      <div
        className={className}
        style={{
          ...style,
          background: "var(--bg-elevated, rgba(255,255,255,0.04))",
          minHeight: 120,
        }}
        aria-label={alt}
      />
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={resolvedSrc}
      alt={alt}
      style={style}
      className={className}
      loading={loading}
      onClick={onClick}
      onLoad={onLoad}
      onError={onError}
    />
  );
}
