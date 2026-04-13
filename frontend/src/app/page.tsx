"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";
import { SlideCardGroup } from "@/components/SlideCard";
import ImageLightbox from "@/components/ImageLightbox";
import type { SlideCard, TranscriptSection } from "@/lib/types";

// ── Demo data from V3.1 pipeline ──────────────────────────────────────

interface DemoSection {
  label: string;
  slides: SlideCard[];
  transcript: TranscriptSection;
}

const DEMO_SECTIONS: DemoSection[] = [
  {
    label: "Baltimore Classification",
    slides: [
      {
        slide_id: "3a",
        title: "The Baltimore Classification System",
        card_type: "professor_slide",
        image_ref: "/screenshots/screenshot_005.jpg",
        bullet_points: [],
        exam_tip:
          "All 7 Baltimore classes must produce +sense mRNA. Positive-sense RNA viruses (Class IV) skip straight to translation. Negative-sense (Class V) and retroviruses (Class VI) need extra enzymatic steps first.",
        ei_percent: 90,
      },
      {
        slide_id: "3b",
        title: "Animal Virus Families by Baltimore Class",
        card_type: "professor_slide",
        image_ref: "/screenshots/screenshot_009.jpg",
        bullet_points: [],
        exam_tip:
          "DNA viruses generally replicate in the host nucleus using host enzymes, while RNA viruses generally replicate in the host cytoplasm using virally encoded RNA-dependent RNA polymerases.",
        ei_percent: 90,
      },
    ],
    transcript: {
      slide_number: 3,
      title: "Baltimore Classification System",
      narrative: `Remember the viral structures we covered earlier\u2014the capsid and the lipid envelope. Those structures protect the viral payload. But what exactly is that payload, and how does it hijack the host cell?

Viruses do not have their own ribosomes. To manufacture their proteins, they must use the host cell\u2019s machinery. The host ribosome only reads one language: messenger RNA (mRNA). Therefore, no matter what genetic material a virus carries inside its capsid, it must find a way to produce mRNA.

This \u201Call roads lead to mRNA\u201D principle is the foundation of the **Baltimore Classification System**. It categorizes viruses into seven distinct classes based on two features: the type of nucleic acid genome they carry, and the specific pathway they use to generate that functional mRNA.

Look at the diagram on the slide. Notice how the arrows from all seven classes converge on that central, golden strand labeled \u201CmRNA (+)\u201D. That is the mandatory destination for every virus.

A positive-sense (+) RNA genome is oriented in the 5\u2019 to 3\u2019 direction, making it physically identical to host mRNA. This means the moment it enters the host cell, the host ribosomes can attach and start translating it directly into viral proteins.

Now look at Class V, the negative-sense (-) ssRNA viruses, which includes the Influenza virus. A negative-sense strand runs in the 3\u2019 to 5\u2019 direction. It is the mirror image to mRNA. A host ribosome cannot read it. Therefore, an Influenza virus must physically carry its own viral enzyme\u2014an **RNA-dependent RNA polymerase**\u2014inside its virion to transcribe that negative strand into a readable positive-sense mRNA.

Both Class IV and Class VI carry a positive-sense ssRNA genome, but use completely different pathways. Class IV, like Poliovirus, uses its +ssRNA directly as mRNA. Class VI, which includes HIV, is a **retrovirus**. Instead of using its +ssRNA directly, it uses **reverse transcriptase** to convert its RNA into a double-stranded DNA intermediate that physically integrates into the host cell\u2019s own chromosome.

The genome dictates the pathway, and the pathway dictates which specific enzymes the virus must bring with it.`,
      ei_percent: 90,
      ei_reasoning: "The Baltimore classification system and the distinction between positive/negative sense RNA are fundamental virology concepts universally tested in medical microbiology curricula.",
    },
  },
  {
    label: "Bacteriophage Structure",
    slides: [
      {
        slide_id: "4a",
        title: "Bacteriophage Anatomy",
        card_type: "professor_slide",
        image_ref: "/screenshots/screenshot_006.jpg",
        bullet_points: [],
        exam_tip:
          "The protein capsid never enters the bacterial cell. It remains outside as an empty \u201Cghost\u201D once the DNA is injected through the contractile sheath.",
        ei_percent: 70,
      },
      {
        slide_id: "4b",
        title: "Receptor Specificity and Genome Entry",
        card_type: "professor_slide",
        image_ref: "/screenshots/screenshot_007.jpg",
        bullet_points: [],
        exam_tip:
          "Different phages bind different bacterial surface structures (flagellum, pilus, outer membrane proteins). Receptor specificity determines host range.",
        ei_percent: 70,
      },
    ],
    transcript: {
      slide_number: 4,
      title: "Bacteriophage Anatomy and Infection",
      narrative: `We\u2019ve previously discussed how viruses are classified by their genomes, but how do they actually get that genetic material inside a host? To understand this, we look at **Bacteriophages**\u2014viruses that specifically infect **Prokaryotes**.

Looking at Slide 4a, notice the complex, almost robotic structure of the T4 phage. It consists of an icosahedral **capsid** (head) containing the DNA, attached to a contractile **sheath**. At the base, you\u2019ll see the **tail fibers**. Think of these fibers as landing gear; they recognize and bind to specific receptors on the bacterial surface.

Once anchored, the real magic happens. The helical sheath contracts\u2014powered by ATP\u2014driving the internal hollow core through the bacterial cell wall like a hypodermic needle. This process, known as **Genome Entry**, is purely mechanical.

On Slide 4b, you can see this receptor specificity in action. Different phages bind to completely different bacterial surface structures\u2014the flagellum, the pilus, outer membrane proteins, even the LPS layer.

A critical distinction for your exams: the protein capsid never enters the cell. It remains outside as an empty \u201Cghost\u201D once the DNA is injected. The virus has now successfully hijacked the host\u2019s machinery, leading us directly into the two pathways it can take: the lytic or lysogenic cycles.`,
      ei_percent: 70,
      ei_reasoning: "Bacteriophage structure and the unique injection mechanism are high-yield topics in microbiology.",
    },
  },
];

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
  const [activeSection, setActiveSection] = useState(0);
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);
  const demo = DEMO_SECTIONS[activeSection];

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

        {/* ───── App Demo — Two-Panel Layout ───── */}
        <section className="pb-20">
          {lightboxSrc && (
            <ImageLightbox src={lightboxSrc} onClose={() => setLightboxSrc(null)} />
          )}

          <div className="rounded-xl overflow-hidden shadow-2xl" style={{ border: "1px solid var(--border)", background: "var(--bg-elevated)" }}>
            {/* Browser chrome + section tabs */}
            <div className="flex items-center gap-2 px-4 py-2.5" style={{ borderBottom: "1px solid var(--border)" }}>
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full" style={{ background: "#ff5f57" }} />
                <div className="w-3 h-3 rounded-full" style={{ background: "#febc2e" }} />
                <div className="w-3 h-3 rounded-full" style={{ background: "#28c840" }} />
              </div>
              <div className="flex-1 mx-4 flex items-center justify-center gap-2">
                {DEMO_SECTIONS.map((s, i) => (
                  <button
                    key={s.label}
                    onClick={() => setActiveSection(i)}
                    className="text-xs px-3 py-1 rounded-md transition-all"
                    style={{
                      background: i === activeSection ? "var(--accent-dim)" : "var(--bg-base)",
                      color: i === activeSection ? "var(--accent)" : "var(--text-muted)",
                      border: `1px solid ${i === activeSection ? "rgba(255,107,53,0.3)" : "transparent"}`,
                    }}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>

            {/* App body — slide card left + transcript right */}
            <div className="flex" style={{ background: "var(--bg-base)", height: 520 }}>
              {/* Left: Slide Card */}
              <div className="hidden sm:flex flex-col w-[45%] shrink-0 p-4 overflow-y-auto" style={{ borderRight: "1px solid var(--border)" }}>
                <SlideCardGroup cards={demo.slides} onImageClick={setLightboxSrc} />
              </div>

              {/* Right: Transcript */}
              <div className="flex-1 overflow-y-auto relative">
                <div className="px-5 sm:px-8 py-5">
                  <h2 className="text-lg font-bold mb-4" style={{ color: "var(--text-primary)" }}>
                    {demo.transcript.title}
                  </h2>
                  {demo.transcript.narrative.split("\n\n").map((para, i) => {
                    const html = para
                      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
                      .replace(/\*\*([\s\S]+?)\*\*/g, '<strong style="color: var(--accent)">$1</strong>')
                      .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "<em>$1</em>");
                    return (
                      <p
                        key={i}
                        className="text-[13px] mb-4 leading-relaxed"
                        style={{ color: "var(--text-secondary)" }}
                        dangerouslySetInnerHTML={{ __html: html }}
                      />
                    );
                  })}
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
