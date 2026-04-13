"use client";

import { useState } from "react";
import { SlideCardGroup } from "@/components/SlideCard";
import NarrativeSection from "@/components/NarrativeSection";
import ImageLightbox from "@/components/ImageLightbox";
import type { SlideCard, TranscriptSection } from "@/lib/types";

// ── V3.1 pipeline output (Lecture 2 — Virology) ────────────────────────

interface PreviewSection {
  slides: SlideCard[];
  transcript: TranscriptSection;
}

const SECTIONS: PreviewSection[] = [
  {
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

// ── Main Preview Page ─────────────────────────────────────────────────
export default function PreviewPage() {
  const [isMobile, setIsMobile] = useState(false);
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);
  const [activeIdx, setActiveIdx] = useState(0);
  const section = SECTIONS[activeIdx];

  return (
    <div
      className="min-h-screen"
      style={{ background: "var(--bg-primary)" }}
    >
      {lightboxSrc && (
        <ImageLightbox src={lightboxSrc} onClose={() => setLightboxSrc(null)} />
      )}

      {/* Header */}
      <div
        className="sticky top-0 z-10 backdrop-blur-xl border-b px-6 py-3 flex items-center justify-between"
        style={{
          background: "rgba(10, 10, 15, 0.85)",
          borderColor: "var(--border)",
        }}
      >
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold" style={{ color: "var(--accent)" }}>
            V3.1 Preview
          </span>
          <div className="flex gap-1.5">
            {SECTIONS.map((s, i) => (
              <button
                key={s.transcript.title}
                onClick={() => setActiveIdx(i)}
                className="text-xs px-2.5 py-1 rounded-md transition-all"
                style={{
                  background: i === activeIdx ? "var(--accent-dim)" : "transparent",
                  color: i === activeIdx ? "var(--accent)" : "var(--text-muted)",
                }}
              >
                {s.transcript.title}
              </button>
            ))}
          </div>
        </div>
        <button
          onClick={() => setIsMobile(!isMobile)}
          className="text-xs px-3 py-1.5 rounded-lg border"
          style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
        >
          {isMobile ? "Desktop" : "Mobile"}
        </button>
      </div>

      {/* Content */}
      <div
        className="max-w-[1400px] mx-auto p-6"
        style={{ maxWidth: isMobile ? "480px" : "1400px" }}
      >
        {isMobile ? (
          <div className="space-y-8">
            <SlideCardGroup cards={section.slides} onImageClick={setLightboxSrc} />
            <NarrativeSection section={section.transcript} />
          </div>
        ) : (
          <div className="grid gap-8" style={{ gridTemplateColumns: "1fr 1fr" }}>
            <div className="space-y-4 sticky top-16 self-start">
              <SlideCardGroup cards={section.slides} onImageClick={setLightboxSrc} />
            </div>
            <div className="pl-8 border-l" style={{ borderColor: "var(--border)" }}>
              <NarrativeSection section={section.transcript} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
