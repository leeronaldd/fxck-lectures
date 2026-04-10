"use client";

import { useRouter } from "next/navigation";

const FEATURES = [
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 20h9" />
        <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
      </svg>
    ),
    title: "Textbook-verified",
    desc: "Every claim fact-checked against OpenStax. Not scraped from blogs and Reddit threads.",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12,6 12,12 16,14" />
      </svg>
    ),
    title: "Smart pacing",
    desc: "Hard concepts get more depth. Professor yap gets skipped. Your time goes where it matters.",
  },
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
    title: "Actually explains",
    desc: "Doesn't assume you already get it. Builds each concept from scratch like a real tutor would.",
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
];

export default function LandingPage() {
  const router = useRouter();

  return (
    <div className="flex-1 relative overflow-hidden">
      {/* Background effects */}
      <div className="hero-glow hero-glow-pulse" />
      <div className="orb orb-orange" style={{ width: 400, height: 400, top: "-10%", right: "10%" }} />
      <div className="orb orb-purple" style={{ width: 300, height: 300, bottom: "20%", left: "5%" }} />

      {/* Top nav — minimal, no hamburger */}
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

      {/* Content */}
      <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6">
        {/* ───── Hero Section ───── */}
        <section className="pt-12 sm:pt-20 pb-12 text-center">
          {/* Badge */}
          <div className="animate-fade-in-up inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass mb-8">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            <span className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
              AI-powered lecture replacement
            </span>
          </div>

          {/* Headline */}
          <h1 className="animate-fade-in-up animation-delay-100 text-4xl sm:text-6xl md:text-7xl font-bold tracking-tight leading-[1.1] mb-6">
            <span className="gradient-text">Fxck Lectures</span>
          </h1>

          {/* Subheadline */}
          <p className="animate-fade-in-up animation-delay-200 text-base sm:text-lg max-w-2xl mx-auto mb-8" style={{ color: "var(--text-secondary)" }}>
            Your 2-hour medical lecture, rewritten as a 15-minute read by a tutor who actually explains things.
          </p>

          {/* CTA button */}
          <div className="animate-fade-in-up animation-delay-300">
            <button
              onClick={() => router.push("/quiz")}
              className="btn-glow px-10 py-4 rounded-xl text-base font-semibold transition-all"
              style={{
                background: "linear-gradient(135deg, var(--accent), #FF8555)",
                color: "#fff",
                boxShadow: "0 8px 32px var(--accent-glow)",
              }}
            >
              Try for free
            </button>
          </div>
        </section>

        {/* ───── Features Grid ───── */}
        <section className="pb-20">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold mb-3" style={{ color: "var(--text-primary)" }}>
              Not another LLM
            </h2>
            <p className="text-sm sm:text-base max-w-lg mx-auto" style={{ color: "var(--text-secondary)" }}>
              Most tools summarise lectures as if you already understood the concept. Klare tutors the concepts from scratch.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {FEATURES.map((f, i) => (
              <div
                key={f.title}
                className={`animate-fade-in-up animation-delay-${(i + 1) * 100} glass card-hover rounded-xl p-6`}
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

        {/* ───── How It Works ───── */}
        <section id="how-it-works" className="pb-20">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold mb-3" style={{ color: "var(--text-primary)" }}>
              How it works
            </h2>
          </div>

          <div className="flex flex-col sm:flex-row items-start gap-4 sm:gap-6">
            {[
              { step: "01", title: "Upload", desc: "Drop your lecture video or transcript" },
              { step: "02", title: "Process", desc: "AI analyzes, fact-checks, and re-explains" },
              { step: "03", title: "Read", desc: "Get a tutor-quality document in 15 minutes" },
            ].map((item, i) => (
              <div key={item.step} className="flex-1 relative">
                <div className="glass rounded-xl p-6 text-center">
                  <div
                    className="text-3xl font-bold mb-3"
                    style={{ color: "var(--accent)", opacity: 0.3 }}
                  >
                    {item.step}
                  </div>
                  <h3 className="text-sm font-semibold mb-1" style={{ color: "var(--text-primary)" }}>
                    {item.title}
                  </h3>
                  <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
                    {item.desc}
                  </p>
                </div>
                {/* Connector arrow (hidden on last item and mobile) */}
                {i < 2 && (
                  <div className="hidden sm:block absolute top-1/2 -right-5 -translate-y-1/2 z-10" style={{ color: "var(--text-muted)" }}>
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M6 3l5 5-5 5" />
                    </svg>
                  </div>
                )}
              </div>
            ))}
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

        {/* ───── Footer ───── */}
        <footer className="pb-8 text-center">
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            Built by <span style={{ color: "var(--accent)" }}>Klare</span>
          </p>
        </footer>
      </div>
    </div>
  );
}
