// Next.js 16 instrumentation hook — loads the right Sentry config based on
// runtime. Silent no-op when DSN is not set, so the app keeps working
// without any Sentry project.
export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("./sentry.server.config");
  }
  if (process.env.NEXT_RUNTIME === "edge") {
    await import("./sentry.edge.config");
  }
}

export { captureRequestError as onRequestError } from "@sentry/nextjs";
