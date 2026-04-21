<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

## Sentry setup (hard-learned)

Two bugs that cost an hour in this session — capturing the fix so future-me doesn't repeat them:

1. **Turbopack requires `instrumentation-client.ts`, NOT `sentry.client.config.ts`.** The old filename works only with webpack. Rename the file; keep the content identical.
2. **`next.config.ts` must be wrapped in `withSentryConfig(...)` from `@sentry/nextjs`.** Without the wrap, the client config isn't injected into the bundle and `Sentry.init()` never runs in the browser. The server/edge configs work fine without it because `instrumentation.ts` is native to Next.

## Vercel deploy gotcha

`NEXT_PUBLIC_*` environment variables are inlined at **build** time by Next.js. Adding one and then clicking "Promote to Production" in Vercel reuses the old preview bundle — the env var won't be present. To apply a new public env var, you must trigger a fresh build (Redeploy with "Use existing Build Cache" **unchecked**).

## Pricing card alignment

The three pricing cards in `settings/page.tsx` have different content heights (Free has no "Billed as..." sub-line, different feature counts). To keep CTA buttons aligned across cards:
- Each card: `flex flex-col`
- Feature `<ul>`: `flex-1`
- Button: `mt-auto`

Don't remove these classes without visually re-checking alignment in both monthly and yearly views.
