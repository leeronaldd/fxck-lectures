import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const nextConfig: NextConfig = {
  // Reverse-proxy PostHog through our own domain so browser-side requests
  // look like same-origin (klareai.com/ingest/*) instead of us.i.posthog.com.
  // Sidesteps CORS blocks from privacy extensions/Brave Shield/strict
  // tracking prevention that would otherwise silently drop our analytics.
  async rewrites() {
    return [
      {
        source: "/ingest/static/:path*",
        destination: "https://us-assets.i.posthog.com/static/:path*",
      },
      {
        source: "/ingest/:path*",
        destination: "https://us.i.posthog.com/:path*",
      },
    ];
  },
  // PostHog SDK is loaded via /ingest/static, so trailing slash must not be
  // auto-added to the proxy path.
  skipTrailingSlashRedirect: true,
};

// Wrap with Sentry so sentry.client.config.ts gets injected into the client
// bundle. Silent no-op if NEXT_PUBLIC_SENTRY_DSN isn't set at build time —
// the generated Sentry.init() call is harmless without a DSN.
export default withSentryConfig(nextConfig, {
  silent: true,
  // Upload source maps only when SENTRY_AUTH_TOKEN is present, so builds
  // don't fail for devs who haven't generated an auth token yet.
  widenClientFileUpload: true,
  disableLogger: true,
});
