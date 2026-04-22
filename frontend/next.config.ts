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
  // Short, trackable bio-link redirects. Each platform bio gets a clean
  // klareai.com/{shortcode} link; the redirect adds UTM params so Vercel
  // Analytics + PostHog can attribute signups to the source platform.
  // Destination can be changed later without updating every bio.
  async redirects() {
    return [
      {
        source: "/ig",
        destination: "/?utm_source=instagram&utm_medium=bio",
        permanent: false,
      },
      {
        source: "/tt",
        destination: "/?utm_source=tiktok&utm_medium=bio",
        permanent: false,
      },
      {
        source: "/yt",
        destination: "/?utm_source=youtube&utm_medium=bio",
        permanent: false,
      },
      {
        source: "/x",
        destination: "/?utm_source=twitter&utm_medium=bio",
        permanent: false,
      },
      {
        source: "/r",
        destination: "/?utm_source=reddit&utm_medium=link",
        permanent: false,
      },
      {
        source: "/ph",
        destination: "/?utm_source=producthunt&utm_medium=launch",
        permanent: false,
      },
      {
        source: "/ih",
        destination: "/?utm_source=indiehackers&utm_medium=post",
        permanent: false,
      },
      {
        source: "/hn",
        destination: "/?utm_source=hackernews&utm_medium=showhn",
        permanent: false,
      },
      {
        source: "/ln",
        destination: "/?utm_source=linkedin&utm_medium=post",
        permanent: false,
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
