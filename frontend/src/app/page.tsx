"use client";

import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";
import InteractiveDemo from "@/components/InteractiveDemo";
import HowKlareWorks from "@/components/HowKlareWorks";

const FAQ_ITEMS = [
  {
    q: "What is Klare?",
    a: "Klare (klareai.com) is an AI study tool for university students. It takes a bad lecture recording or transcript and re-teaches the concepts from scratch — like a personal tutor — producing a clear 20-minute read instead of the original 2-hour lecture. It's free to try, no credit card required.",
  },
  {
    q: "How is Klare different from NotebookLM, Studley, or Turbo AI?",
    a: "NotebookLM, Studley, and Turbo AI clean up and organise what your professor said. Klare does the opposite — it discards the professor's explanation entirely and re-teaches each concept using concrete examples, verified against OpenStax and medical textbooks. If your professor explains things badly, Klare fixes that at the root.",
  },
  {
    q: "Does Klare work for medical, biomed, or nursing students?",
    a: "Yes. Klare was built specifically for health science students — medical, biomed, nursing, pharmacology, anatomy, and physiology. It's fact-checked against OpenStax, NCBI, and PubMed, and it knows which concepts are exam-critical so it gives depth where it counts.",
  },
  {
    q: "How accurate is Klare? Will it hallucinate?",
    a: "Every claim in a Klare document is verified against OpenStax, NCBI, or PubMed during generation. A second AI then cross-checks the output against the original lecture and patches any gaps. Klare corrects transcript errors like misspellings and muffled terms, but won't invent facts.",
  },
  {
    q: "How long does Klare take to process a lecture?",
    a: "Most lectures process in 4–6 minutes. A standard 1-hour lecture produces a 20–30 minute read. Processing time is roughly constant regardless of whether your lecture is 45 minutes or 2 hours.",
  },
  {
    q: "What file types does Klare accept?",
    a: "Klare accepts MP4 video, MP3 audio, PDF slides, and plain text transcripts. You can upload a lecture recording, a set of slides, or a transcript you already have — or all three together for best results.",
  },
  {
    q: "Can Klare understand lectures with heavy accents or unclear audio?",
    a: "Yes. Klare uses Whisper-based transcription which handles a wide range of accents and audio quality. Even if the transcript has errors, Klare's AI corrects common misspellings and muffled terms against known textbook terminology during the re-teaching step.",
  },
  {
    q: "Will Klare miss content from my lecture?",
    a: "Unlikely. After generating the study document, a second AI reads your original lecture transcript and cross-checks it against the output — anything missed gets patched in automatically. You also see an exam-importance rating per section so you know what got full coverage versus a quick mention.",
  },
  {
    q: "How much does Klare cost?",
    a: "Klare has a free tier — one lecture, no credit card required. Paid plans are billed in AUD monthly or yearly. See full pricing at klareai.com/settings.",
  },
];

const FAQ_SCHEMA = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: FAQ_ITEMS.map(({ q, a }) => ({
    "@type": "Question",
    name: q,
    acceptedAnswer: { "@type": "Answer", text: a },
  })),
};

const FEATURES = [
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
        <polyline points="14,2 14,8 20,8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10,9 9,9 8,9" />
      </svg>
    ),
    title: "Organic Chemistry Tutor Quality Explanation",
    desc: "Klare AI is trained to match Organic Chemistry Tutor quality explanation. Build each concept from scratch like a real tutor would.",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 20h9" />
        <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
      </svg>
    ),
    title: "Textbook-verified",
    desc: "Every claim fact-checked against OpenStax, NCBI, or PubMed.",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12,6 12,12 16,14" />
      </svg>
    ),
    title: "Smart pacing",
    desc: "Hard concepts get more depth. Easy concepts go straight to point. Professor yap gets one sentence.",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="13,2 3,14 12,14 11,22 21,10 12,10" />
      </svg>
    ),
    title: "Exam-aware",
    desc: "Flags what's likely tested, what's safe to skip, and what your professor skimmed but you still need to know.",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 11l3 3L22 4" />
        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
      </svg>
    ),
    title: "Nothing left behind",
    desc: "After writing, a second AI reads your raw lecture and cross-checks the output. Anything that didn't make it in gets patched automatically — so the final output covers the lecture, not just the highlights.",
    span2: true,
  },
];

export default function LandingPage() {
  const router = useRouter();
  const { user } = useAppStore();
  const isLoggedIn = user.isLoggedIn;

  return (
    <div className="flex-1 relative overflow-hidden">
      {/* Background effects */}
      <div className="hero-glow hero-glow-pulse" />
      <div className="orb orb-orange" style={{ width: 400, height: 400, top: "-10%", right: "10%" }} />
      <div className="orb orb-purple" style={{ width: 300, height: 300, bottom: "20%", left: "5%" }} />

      {/* Top nav — only show for guests (logged-in users have AppShell header) */}
      {!isLoggedIn && (
        <header
          className="relative z-20 flex items-center justify-between px-6 sm:px-10 py-4"
        >
          <img src="/brand/logo-full-dark.svg" alt="Klare" className="h-7" />
          <button
            onClick={() => router.push("/signin")}
            className="text-xs px-4 py-2 rounded-lg font-medium transition-all"
            style={{
              background: "var(--accent-dim)",
              color: "var(--accent)",
              border: "1px solid rgba(255, 107, 53, 0.2)",
            }}
          >
            Sign In
          </button>
        </header>
      )}

      {/* Content */}
      <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6">
        {/* ───── Hero Section ───── */}
        <section className="pt-12 sm:pt-20 pb-12 text-center">
          {/* Audience pill */}
          <div
            className="animate-fade-in-up animation-delay-100 inline-flex items-center gap-2 px-3 py-1.5 rounded-full mb-6 text-xs font-medium"
            style={{
              background: "var(--accent-dim)",
              color: "var(--accent)",
              border: "1px solid rgba(255, 107, 53, 0.2)",
            }}
          >
            <span className="w-1.5 h-1.5 rounded-full animate-pulse-dot" style={{ background: "var(--accent)" }} />
            For medical, health sci &amp; biomed students
          </div>

          {/* Headline */}
          <h1 className="animate-fade-in-up animation-delay-200 text-4xl sm:text-6xl md:text-7xl font-bold tracking-tight leading-[1.1] mb-6">
            Lectures, <span className="gradient-text">taught better.</span>
          </h1>

          {/* Subheadline */}
          <p className="animate-fade-in-up animation-delay-300 text-base sm:text-lg max-w-2xl mx-auto mb-8" style={{ color: "var(--text-secondary)" }}>
            Turns that one bad professor&rsquo;s 2-hour lecture into a 20-minute read that actually makes sense.
          </p>

          {/* CTA button */}
          <div className="animate-fade-in-up animation-delay-400">
            <button
              onClick={() => router.push("/quiz")}
              className="btn-glow px-10 py-4 rounded-xl text-base font-semibold transition-all"
              style={{
                background: "linear-gradient(135deg, var(--accent), #FF8555)",
                color: "#fff",
                boxShadow: "0 8px 32px var(--accent-glow)",
              }}
            >
              Try it for Free
            </button>
            <p className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
              Free &middot; no card required
            </p>

            {/* Coming-soon teaser → routes to signup, account auto-joins waitlist */}
            <div className="mt-4 flex justify-center">
              <button
                type="button"
                onClick={() => router.push("/quiz")}
                className="group inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-medium transition-all hover:opacity-90"
                style={{
                  background: "var(--accent-dim)",
                  color: "var(--accent)",
                  border: "1px solid rgba(255, 107, 53, 0.2)",
                }}
              >
                <span aria-hidden>🎬</span>
                <span>Video explanations coming next — sign up to join waitlist</span>
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="transition-transform group-hover:translate-x-0.5"
                  aria-hidden="true"
                >
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </button>
            </div>

            {/* Secondary low-commitment path — keeps browsers on the page */}
            <button
              type="button"
              onClick={() => {
                document.getElementById("interactive-demo")?.scrollIntoView({
                  behavior: "smooth",
                  block: "start",
                });
              }}
              className="read-sample-link mt-6 inline-flex items-center gap-1.5 text-sm font-medium transition-opacity hover:opacity-100"
              style={{ color: "var(--accent)", opacity: 0.85 }}
            >
              See it in action
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="read-sample-arrow"
                aria-hidden="true"
              >
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </button>
          </div>
        </section>

        {/* ───── Interactive Demo ───── */}
        <section id="interactive-demo" className="pb-20 scroll-mt-20">
          <InteractiveDemo />
        </section>

        {/* ───── Features Grid ───── */}
        <section className="pb-20">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold mb-3" style={{ color: "var(--text-primary)" }}>
              Other tools make bad lectures prettier. We fix them.
            </h2>
            <p className="text-sm sm:text-base max-w-lg mx-auto" style={{ color: "var(--text-secondary)" }}>
              They summarise. We re-teach.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {FEATURES.map((f, i) => (
              <div
                key={f.title}
                className={`animate-fade-in-up animation-delay-${(i + 1) * 100} glass card-hover rounded-xl p-6${"span2" in f && f.span2 ? " sm:col-span-2" : ""}`}
              >
                <div
                  className="w-10 h-10 rounded-lg flex items-center justify-center mb-4"
                  style={{ background: "var(--accent-dim)", color: "var(--accent)" }}
                >
                  {f.icon}
                </div>
                <h3 className="text-sm font-semibold mb-1.5" style={{ color: "var(--text-primary)" }}>
                  {f.title}
                </h3>
                <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                  {f.desc}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* ───── How does Klare work? ───── */}
        <HowKlareWorks />

        {/* ───── Testimonial ───── */}
        <section className="pb-20">
          <div className="max-w-3xl mx-auto">
            <div
              className="glass rounded-2xl p-8 sm:p-10 relative"
              style={{ borderColor: "var(--border-glass)" }}
            >
              <svg
                className="absolute top-5 left-5 opacity-25"
                width="32"
                height="32"
                viewBox="0 0 24 24"
                fill="var(--accent)"
                aria-hidden="true"
              >
                <path d="M10 11H6a2 2 0 01-2-2V7a4 4 0 014-4h2v4H8a2 2 0 00-2 2h4v2zm10 0h-4a2 2 0 01-2-2V7a4 4 0 014-4h2v4h-2a2 2 0 00-2 2h4v2z" />
              </svg>
              <p
                className="text-base sm:text-lg leading-relaxed mb-6 pl-10"
                style={{ color: "var(--text-primary)" }}
              >
                &ldquo;Btw my brother made this for me &mdash; I used to spend hours just trying to understand what my micro prof was saying. Now it&rsquo;s 20 mins to learn the lecture, 30 to memorise.&rdquo;
              </p>
              <div className="flex items-center gap-3 pl-10">
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
                  style={{ background: "var(--accent-dim)", color: "var(--accent)" }}
                  aria-hidden
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </div>
                <div>
                  <div className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                    Anonymous
                  </div>
                  <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                    1st-year Pre-med student
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ───── CTA Banner ───── */}
        <section className="pb-24">
          <div
            className="rounded-2xl p-8 sm:p-12 text-center relative overflow-hidden"
            style={{
              background: "linear-gradient(135deg, rgba(255,107,53,0.1), rgba(139,92,246,0.08))",
              border: "1px solid rgba(255,107,53,0.15)",
            }}
          >
            <h2 className="text-xl sm:text-2xl font-bold mb-3" style={{ color: "var(--text-primary)" }}>
              Your next lecture doesn't have to suck
            </h2>
            <p className="text-sm mb-6 max-w-md mx-auto" style={{ color: "var(--text-secondary)" }}>
              Join students who replaced hours of bad lectures with 15-minute reads.
            </p>
            <button
              onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
              className="btn-glow px-8 py-3 rounded-xl text-sm font-semibold"
              style={{
                background: "linear-gradient(135deg, var(--accent), #FF8555)",
                color: "#fff",
                boxShadow: "0 8px 32px var(--accent-glow)",
              }}
            >
              Try it free
            </button>
          </div>
        </section>

        {/* ───── FAQ ───── */}
        <section id="faq" className="pb-20 scroll-mt-20">
          <div className="text-center mb-10">
            <h2 className="text-2xl sm:text-3xl font-bold mb-3" style={{ color: "var(--text-primary)" }}>
              Common questions
            </h2>
          </div>
          <div className="space-y-3 max-w-2xl mx-auto">
            {FAQ_ITEMS.map(({ q, a }) => (
              <details key={q} className="glass rounded-xl group" style={{ borderColor: "var(--border-glass)" }}>
                <summary
                  className="flex items-center justify-between px-6 py-4 cursor-pointer select-none list-none"
                  style={{ color: "var(--text-primary)" }}
                >
                  <span className="text-sm font-medium pr-4">{q}</span>
                  <svg
                    className="shrink-0 transition-transform duration-200 group-open:rotate-180"
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    style={{ color: "var(--accent)" }}
                  >
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </summary>
                <p className="px-6 pb-5 text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                  {a}
                </p>
              </details>
            ))}
          </div>
        </section>

        {/* FAQ JSON-LD schema for AEO */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(FAQ_SCHEMA) }}
        />

        {/* ───── Footer ───── */}
        <footer className="pb-8 text-center space-y-2">
          <div className="flex items-center justify-center gap-4 text-xs" style={{ color: "var(--text-muted)" }}>
            <a href="/terms" className="hover:opacity-80 underline-offset-4 hover:underline">Terms</a>
            <span>·</span>
            <a href="/privacy" className="hover:opacity-80 underline-offset-4 hover:underline">Privacy</a>
            <span>·</span>
            <a href="mailto:hello@klareai.com" className="hover:opacity-80 underline-offset-4 hover:underline">Contact</a>
          </div>
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            Built by <span style={{ color: "var(--accent)" }}>Klare</span>
          </p>
        </footer>
      </div>
    </div>
  );
}
