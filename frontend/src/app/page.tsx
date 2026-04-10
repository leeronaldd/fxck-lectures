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

        {/* ───── Animated App Demo ───── */}
        <section className="pb-20">
          {/* Browser mockup — wide horizontal layout with fake sidebar */}
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

            {/* App body — sidebar + content */}
            <div className="flex" style={{ background: "var(--bg-base)", height: 480 }}>
              {/* Fake sidebar */}
              <div className="hidden sm:flex flex-col w-[200px] shrink-0 p-3 gap-2" style={{ borderRight: "1px solid var(--border)", background: "rgba(10,10,15,0.95)" }}>
                <div className="flex items-center gap-2 px-2 py-2 rounded-lg text-xs font-medium" style={{ background: "var(--accent-dim)", color: "var(--accent)" }}>
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M8 3v10M3 8h10" /></svg>
                  New Session
                </div>
                <p className="px-2 pt-2 text-[9px] font-semibold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Recent</p>
                {/* Animated session appearing */}
                <div className="demo-reveal demo-reveal-1 px-2 py-2 rounded-lg" style={{ background: "var(--bg-elevated)" }}>
                  <p className="text-xs truncate" style={{ color: "var(--text-primary)" }}>Microbiology Lec 4</p>
                  <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>Apr 9, 2026</p>
                </div>
                <div className="demo-reveal demo-reveal-2 px-2 py-2 rounded-lg">
                  <p className="text-xs truncate" style={{ color: "var(--text-secondary)" }}>Neuroscience of Habit</p>
                  <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>Apr 10, 2026</p>
                </div>
              </div>

              {/* Scrolling content area */}
              <div className="flex-1 overflow-hidden relative">
                <div className="demo-scroll-content px-6 sm:px-12 py-6">
                  <div className="demo-reveal demo-reveal-1">
                    <h2 className="text-lg font-bold mb-4" style={{ color: "var(--text-primary)" }}>The Baltimore Classification System</h2>
                  </div>

                  <div className="demo-reveal demo-reveal-2">
                    <p className="text-sm mb-4 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      Imagine trying to play a PlayStation 5 game on an Xbox. It doesn&apos;t matter how incredible the game is; the console just can&apos;t read the disc. Viruses face the exact same problem when they break into our cells.
                    </p>
                  </div>

                  <div className="demo-reveal demo-reveal-3">
                    <p className="text-sm mb-4 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      As we covered earlier, viruses are <span style={{ color: "var(--accent)" }}>obligate intracellular parasites</span>&mdash;they have to hijack a host cell to survive. But just getting inside isn&apos;t enough. To make new <span style={{ color: "var(--accent)" }}>virions</span> (fully assembled virus particles), the virus has to hand its genetic instructions over to our cell&apos;s machinery to build viral proteins. The problem? Viruses carry their genomes in all sorts of weird formats, while our cells only naturally know how to read one specific sequence: DNA to RNA to Protein.
                    </p>
                  </div>

                  <div className="demo-reveal demo-reveal-4">
                    <div className="rounded-lg p-4 mb-5" style={{ background: "rgba(255,107,53,0.08)", borderLeft: "3px solid var(--accent)" }}>
                      <p className="text-sm leading-relaxed" style={{ color: "var(--text-primary)" }}>
                        To make sense of this mess, we use the <strong style={{ color: "var(--accent)" }}>Baltimore Classification System</strong>. You absolutely need to know this for your exam. It groups viruses into seven classes based on one simple question: <em>How does this virus get its genome turned into mRNA?</em>
                      </p>
                    </div>
                  </div>

                  <div className="demo-reveal demo-reveal-5">
                    <p className="text-sm mb-4 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      Before we look at the groups, we need to clear up a massive stumbling block: RNA sense.
                    </p>
                    <p className="text-sm mb-3 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      Our cells read <strong style={{ color: "var(--text-primary)" }}>mRNA</strong> (messenger RNA) to build proteins.
                    </p>
                  </div>

                  <div className="demo-reveal demo-reveal-6">
                    <div className="ml-4 mb-3">
                      <p className="text-sm leading-relaxed mb-3" style={{ color: "var(--text-secondary)" }}>
                        If a virus has <span style={{ color: "var(--accent)" }}>positive-sense (+)</span> RNA, it has it easy. This RNA is basically a perfectly formatted mRNA molecule. Our cellular machinery can read it and start building viral proteins the second it enters the cell.
                      </p>
                      <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                        If a virus has <span style={{ color: "var(--accent)" }}>negative-sense (-)</span> RNA, it&apos;s like handing the cell a blueprint written entirely in reverse. Our machinery can&apos;t read it. The virus has to make a complementary positive-sense copy before anything else can happen.
                      </p>
                    </div>
                  </div>

                  <div className="demo-reveal demo-reveal-7">
                    <p className="text-sm mb-4 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      Now, let&apos;s group the seven Baltimore classes logically so you don&apos;t have to blindly memorize them.
                    </p>
                  </div>

                  <div className="demo-reveal demo-reveal-8">
                    <h3 className="text-base font-bold mb-2 mt-4" style={{ color: "var(--text-primary)" }}>
                      {"\uD83E\uDDEA"} The Traditionalists: DNA Viruses
                    </h3>
                    <p className="text-sm mb-3 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      These guys play by our cell&apos;s rules. Our cells normally transcribe double-stranded DNA into mRNA, so these viruses fit right in.
                    </p>
                  </div>

                  <div className="demo-reveal demo-reveal-9">
                    <p className="text-sm mb-3 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      <strong style={{ color: "var(--accent)" }}>Group I: Double-stranded DNA (dsDNA).</strong> This is exactly what our own cells use. The virus just hands its dsDNA over to our cellular enzymes, which transcribe it into mRNA. Easy.
                    </p>
                    <p className="text-sm mb-3 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      <strong style={{ color: "var(--accent)" }}>Group II: Single-stranded DNA (ssDNA).</strong> Our cells don&apos;t like single-stranded DNA. So, the first step is for the host cell to build a second DNA strand, temporarily turning it into dsDNA. From there, it acts exactly like Group I.
                    </p>
                  </div>

                  <div className="demo-reveal demo-reveal-10">
                    <h3 className="text-base font-bold mb-2 mt-4" style={{ color: "var(--text-primary)" }}>
                      {"\uD83C\uDFC3"} The Fast Trackers: Ready-to-Go RNA
                    </h3>
                    <p className="text-sm mb-3 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      <strong style={{ color: "var(--accent)" }}>Group IV: Positive-sense single-stranded RNA (+ssRNA).</strong> These viruses don&apos;t even need to visit the nucleus. The moment they enter the cell, our ribosomes (the protein builders) latch onto the +ssRNA and start translating it into viral proteins immediately.
                    </p>
                  </div>

                  <div className="demo-reveal demo-reveal-11">
                    <h3 className="text-base font-bold mb-2 mt-4" style={{ color: "var(--text-primary)" }}>
                      {"\uD83E\uDE9E"} The Mirror-Image RNA
                    </h3>
                    <p className="text-sm mb-3 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      <strong style={{ color: "var(--accent)" }}>Group III: Double-stranded RNA (dsRNA).</strong> The virus uses the negative strand as a template to churn out positive-sense mRNA.
                    </p>
                    <p className="text-sm mb-3 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      <strong style={{ color: "var(--accent)" }}>Group V: Negative-sense single-stranded RNA (-ssRNA).</strong> This genome is backwards. The virus <em>must</em> pack its own polymerase enzyme inside its capsid. As soon as it enters, that enzyme reads the negative strand and transcribes it into positive-sense mRNA. Think Ebola, measles, rabies.
                    </p>
                  </div>

                  <div className="demo-reveal demo-reveal-12">
                    <h3 className="text-base font-bold mb-2 mt-4" style={{ color: "var(--text-primary)" }}>
                      {"\uD83D\uDD75\uFE0F"} The Rule Breakers
                    </h3>
                    <p className="text-sm mb-3 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      <strong style={{ color: "var(--accent)" }}>Group VI: Retroviruses (+ssRNA).</strong> These viruses have positive-sense RNA, but they <em>don&apos;t</em> use it as mRNA. Instead, they carry <strong style={{ color: "var(--accent)" }}>reverse transcriptase</strong> which converts their RNA into DNA. That viral DNA then permanently stitches itself into the host cell&apos;s own DNA. HIV is the poster child.
                    </p>
                    <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      <strong style={{ color: "var(--accent)" }}>Group VII: dsDNA with Reverse Transcriptase.</strong> Viruses like Hepatitis B start with dsDNA. They transcribe it into mRNA normally, but to package new genomes, they use reverse transcriptase to turn that mRNA <em>back</em> into dsDNA. Completely chaotic, but it works.
                    </p>
                  </div>
                </div>

                {/* Fade overlays top and bottom */}
                <div className="absolute top-0 left-0 right-0 h-8 pointer-events-none" style={{ background: "linear-gradient(var(--bg-base), transparent)" }} />
                <div className="absolute bottom-0 left-0 right-0 h-16 pointer-events-none" style={{ background: "linear-gradient(transparent, var(--bg-base))" }} />
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
