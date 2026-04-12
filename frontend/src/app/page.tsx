"use client";

import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";

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

        {/* ───── V2 App Demo — Two-Panel Layout ───── */}
        <section className="pb-20">
          <div className="rounded-xl overflow-hidden shadow-2xl" style={{ border: "1px solid var(--border)", background: "var(--bg-elevated)" }}>
            {/* Browser chrome */}
            <div className="flex items-center gap-2 px-4 py-2.5" style={{ borderBottom: "1px solid var(--border)" }}>
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full" style={{ background: "#ff5f57" }} />
                <div className="w-3 h-3 rounded-full" style={{ background: "#febc2e" }} />
                <div className="w-3 h-3 rounded-full" style={{ background: "#28c840" }} />
              </div>
              <div className="flex-1 mx-4">
                <div className="text-xs px-3 py-1 rounded-md text-center" style={{ background: "var(--bg-base)", color: "var(--text-muted)" }}>
                  fxck-lectures.vercel.app/reader
                </div>
              </div>
            </div>

            {/* App body — slide card left + transcript right */}
            <div className="flex" style={{ background: "var(--bg-base)", height: 520 }}>
              {/* Left: Slide Card */}
              <div className="hidden sm:flex flex-col w-[45%] shrink-0 p-4 overflow-y-auto" style={{ borderRight: "1px solid var(--border)" }}>
                <div className="demo-reveal demo-reveal-1 rounded-xl overflow-hidden border" style={{ background: "var(--bg-surface)", borderColor: "var(--border)" }}>
                  {/* Card header */}
                  <div className="px-4 py-2.5 flex items-center justify-between border-b" style={{ borderColor: "var(--border)" }}>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold px-1.5 py-0.5 rounded-md" style={{ background: "var(--accent-dim)", color: "var(--accent)" }}>1a</span>
                      <span className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>The Baltimore Classification System</span>
                    </div>
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full" style={{ background: "rgba(255,176,32,0.15)", color: "var(--ci-high)" }}>EI 90%</span>
                  </div>
                  {/* Slide image */}
                  <div className="p-2.5">
                    <div className="rounded-lg overflow-hidden bg-white">
                      <img src="/screenshots/screenshot_005.jpg" alt="Baltimore Classification System" className="w-full h-auto" />
                    </div>
                  </div>
                  {/* Exam tip */}
                  <div className="px-4 py-2.5 text-[11px] border-t" style={{ borderColor: "var(--border)", background: "var(--exam-bg)", color: "var(--ci-high)" }}>
                    <span className="font-semibold">Exam tip:</span> All 7 Baltimore classes must produce +sense mRNA. Positive-sense RNA viruses (Class IV) skip straight to translation. Negative-sense (Class V) and retroviruses (Class VI) need extra enzymatic steps first.
                  </div>
                </div>

                {/* Sub-slide indicators */}
                <div className="demo-reveal demo-reveal-2 flex items-center justify-center gap-2 py-3">
                  <span className="text-[10px] px-2 py-1 rounded-full border font-mono" style={{ background: "var(--accent-dim)", color: "var(--accent)", borderColor: "var(--accent)" }}>1a</span>
                  <span className="text-[10px] px-2 py-1 rounded-full border font-mono" style={{ color: "var(--text-muted)", borderColor: "var(--border)" }}>1b</span>
                </div>
              </div>

              {/* Right: Transcript */}
              <div className="flex-1 overflow-y-auto relative">
                <div className="demo-scroll-content px-5 sm:px-8 py-5">
                  <div className="demo-reveal demo-reveal-1">
                    <h2 className="text-lg font-bold mb-4" style={{ color: "var(--text-primary)" }}>Baltimore Classification System</h2>
                  </div>

                  <div className="demo-reveal demo-reveal-2">
                    <p className="text-[13px] mb-4 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      We&apos;ve established how viruses are categorized by their physical structures, like the capsids and stolen envelopes we covered in Section 1. But if you&apos;re a virus, looking pretty doesn&apos;t replicate your genome. How do you actually hijack a cell? To understand how viruses function, we have to look at their genetic architecture.
                    </p>
                  </div>

                  <div className="demo-reveal demo-reveal-3">
                    <p className="text-[13px] mb-4 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      Nucleic acids have a physical direction. One end exposes the fifth carbon&mdash;the <strong style={{ color: "var(--accent)" }}>5&apos; end</strong>. The opposite end exposes the third carbon&mdash;the <strong style={{ color: "var(--accent)" }}>3&apos; end</strong>. We call the 5&apos; to 3&apos; strand the <strong style={{ color: "var(--accent)" }}>positive sense</strong> strand. It &ldquo;makes sense&rdquo; to the host cell&mdash;it reads exactly like the host&apos;s own messenger RNA. The opposite strand is the <strong style={{ color: "var(--accent)" }}>negative sense</strong> strand. Think of it like a photographic negative.
                    </p>
                  </div>

                  <div className="demo-reveal demo-reveal-4">
                    <p className="text-[13px] mb-4 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      This brings us to the central problem every virus faces. To survive, it must force the host cell to build viral <strong style={{ color: "var(--accent)" }}>proteins</strong>. But ribosomes only read one language: positive-sense mRNA. Every single virus must eventually produce a positive-sense mRNA intermediate.
                    </p>
                  </div>

                  <div className="demo-reveal demo-reveal-5">
                    <p className="text-[13px] mb-4 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      Look at the diagram on the slide. This is the <strong style={{ color: "var(--accent)" }}>Baltimore classification system</strong>. Notice how all seven pathways converge on that same central box: mRNA. It categorizes all viruses into 7 groups based on their nucleic acid type, their strandedness, and the specific pathway they use to reach that mRNA step.
                    </p>
                  </div>

                  <div className="demo-reveal demo-reveal-6">
                    <p className="text-[13px] mb-4 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      <strong style={{ color: "var(--accent)" }}>Class I</strong> (dsDNA) uses host RNA polymerase directly. <strong style={{ color: "var(--accent)" }}>Class II</strong> (ssDNA) must first build a complementary strand. <strong style={{ color: "var(--accent)" }}>Class IV</strong> (+ssRNA) is the most direct&mdash;the genome itself functions as mRNA, and ribosomes begin translation immediately.
                    </p>
                  </div>

                  <div className="demo-reveal demo-reveal-7">
                    <p className="text-[13px] mb-3 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      <strong style={{ color: "var(--accent)" }}>Class V</strong> (&minus;ssRNA), like <em>influenza</em>, must first transcribe its negative-sense genome into positive-sense mRNA. <strong style={{ color: "var(--accent)" }}>Class VI</strong> retroviruses deploy <strong style={{ color: "var(--accent)" }}>reverse transcriptase</strong> to convert RNA backwards into DNA that integrates into the host genome. HIV is the classic example.
                    </p>
                  </div>

                  <div className="demo-reveal demo-reveal-8">
                    <p className="text-[13px] mb-3 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      <strong style={{ color: "var(--accent)" }}>Class VII</strong> (hepadnaviruses, like Hepatitis B) contains gapped DNA. The host repairs the gap, transcribes mRNA normally, but then reverse-transcribes that mRNA back into gapped DNA to replicate. So we know all roads lead to mRNA. Let&apos;s trace how these viruses actually get inside a host cell...
                    </p>
                  </div>
                </div>

                {/* Fade overlays */}
                <div className="absolute top-0 left-0 right-0 h-6 pointer-events-none" style={{ background: "linear-gradient(var(--bg-base), transparent)" }} />
                <div className="absolute bottom-0 left-0 right-0 h-12 pointer-events-none" style={{ background: "linear-gradient(transparent, var(--bg-base))" }} />
              </div>
            </div>
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
