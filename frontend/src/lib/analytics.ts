"use client";

import posthog from "posthog-js";

// Lazy init — only boot PostHog in the browser, only once, only if the
// key is set. If NEXT_PUBLIC_POSTHOG_KEY isn't in the env, every capture()
// call becomes a no-op so dev + preview builds stay silent.
let booted = false;
function boot() {
  if (booted || typeof window === "undefined") return;
  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
  if (!key) return;
  posthog.init(key, {
    // Route through our Next.js reverse proxy (see next.config.ts rewrites)
    // so browser-side requests are same-origin and don't get killed by
    // privacy extensions / Brave / strict tracking prevention.
    api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || "/ingest",
    ui_host: "https://us.posthog.com",
    person_profiles: "identified_only",
    capture_pageview: true,
    capture_pageleave: true,
  });
  booted = true;
}

export function trackEvent(
  event: string,
  properties?: Record<string, unknown>
) {
  boot();
  if (!booted) return;
  posthog.capture(event, properties);
}

export function identifyUser(
  userId: string,
  traits?: Record<string, unknown>
) {
  boot();
  if (!booted) return;
  posthog.identify(userId, traits);
}

export function resetUser() {
  if (!booted) return;
  posthog.reset();
}
