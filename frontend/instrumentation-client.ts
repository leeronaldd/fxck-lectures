// Runs in the browser. No-ops silently if NEXT_PUBLIC_SENTRY_DSN is not set,
// so the app keeps working until you create a Sentry project and paste the
// DSN into Vercel env vars.
import * as Sentry from "@sentry/nextjs";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (dsn) {
  Sentry.init({
    dsn,
    // Keep sample rates low until you're sure you're not going to burn
    // through the free 5k events/month plan. 10% catches trends without
    // costing you anything at 100 users.
    tracesSampleRate: 0.1,
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 1.0,
    // Strip obvious PII from events before they leave the browser.
    beforeSend(event) {
      if (event.request?.cookies) delete event.request.cookies;
      if (event.user?.ip_address) event.user.ip_address = undefined;
      return event;
    },
    environment: process.env.NODE_ENV,
  });
}
