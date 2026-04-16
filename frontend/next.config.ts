import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const nextConfig: NextConfig = {
  /* config options here */
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
