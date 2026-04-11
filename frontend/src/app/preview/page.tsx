"use client";

import { useState } from "react";
import { SlideCardGroup } from "@/components/SlideCard";
import NarrativeSection from "@/components/NarrativeSection";
import ImageLightbox from "@/components/ImageLightbox";
import type { SlideCard, TranscriptSection } from "@/lib/types";

// ── Test data from V2 pipeline (Baltimore Classification — all 7 classes) ────
const TEST_SLIDES: SlideCard[] = [
  {
    slide_id: "1a",
    title: "The Baltimore Classification System",
    card_type: "professor_slide",
    image_ref: "screenshots/screenshot_005.jpg",
    bullet_points: [],
    exam_tip:
      "Positive-sense (+ssRNA) viruses can be translated directly by host ribosomes, whereas negative-sense (\u2212ssRNA) viruses must carry RNA-dependent RNA polymerase in their virion to synthesize a readable positive strand first.",
    ei_percent: 90,
  },
  {
    slide_id: "1b",
    title: "Animal Virus Families by Baltimore Class",
    card_type: "professor_slide",
    image_ref: "screenshots/screenshot_009.jpg",
    bullet_points: [],
    exam_tip:
      "DNA viruses generally replicate in the host nucleus using host enzymes, while RNA viruses generally replicate in the host cytoplasm using virally encoded RNA-dependent RNA polymerases.",
    ei_percent: 90,
  },
];

const TEST_TRANSCRIPT: TranscriptSection[] = [
  {
    slide_number: 1,
    title: "Baltimore Classification System",
    narrative: `Remember back in Module 1, we established that cellular DNA replicates via semi-conservative replication. The two double-helix strands separate, and each acts as a physical template to synthesize a new complementary strand. Every living cell uses this exact same starting material\u2014double-stranded DNA\u2014to store information, which it then transcribes into messenger RNA to build proteins.

Viruses, however, are essentially genetic hijackers. Every virus has one ultimate goal when it enters a host cell: to synthesize viral proteins. But to make proteins, you need messenger RNA. Where does a virus get it?

Look at the diagram on the slide. Right in the middle, you see mRNA highlighted in yellow. Notice how every single grey arrow points directly to it. This is the **Baltimore classification system**. It categorizes all viruses based on two physical traits: the structure of their genome, and the specific enzymatic pathway they use to reach that central mRNA step.

Before we trace those arrows, we need to establish the physical orientation of the genetic material. Look at the text at the top of the slide. A nucleic acid strand has a direction, read from the 5-prime carbon of the ribose sugar to the 3-prime carbon. We call this 5-prime to 3-prime orientation the **positive sense**.

Messenger RNA is always positive sense. It arrives at the host ribosome perfectly formatted and ready to be read. The complementary strand runs in the opposite direction, from 3-prime to 5-prime. We call this the **negative sense**. A negative sense strand cannot be translated by a ribosome; it is a mirror image that must first be transcribed into a positive sense strand.

Your professor glossed over the individual viral classes, but you will consistently see them on board exams. Let\u2019s walk through the main pathways these viruses use to generate mRNA.

Classes I and II start with DNA. Class I viruses possess double-stranded DNA, so they simply enter the host nucleus and use the host\u2019s own DNA-dependent RNA polymerase to transcribe mRNA, exactly like a normal cell. Class II viruses possess single-stranded DNA, so they must first synthesize a complementary DNA strand to form a double-stranded intermediate before transcription can occur.

Classes III, IV, and V start with RNA. This presents a unique mechanical problem: host cells do not possess enzymes that can read an RNA template to build a new RNA strand. Therefore, these viruses must utilize a viral-encoded enzyme called **RNA-dependent RNA polymerase**.

Class IV viruses possess positive-sense single-stranded RNA. Because it is already in the 5-prime to 3-prime orientation, the viral genome acts directly as mRNA the moment it enters the cell. The host ribosomes immediately translate it. Class V viruses possess negative-sense single-stranded RNA. They must physically carry RNA-dependent RNA polymerase inside their viral capsule. Upon entry, this enzyme reads the negative-sense genome and transcribes a positive-sense mRNA strand.

Class VI and VII viruses utilize a completely different mechanism involving **reverse transcriptase**, an enzyme that reads an RNA template to synthesize DNA. Class VI viruses, the retroviruses, enter with a positive-sense RNA genome. Instead of translating it directly, reverse transcriptase converts this RNA into double-stranded DNA, which then physically integrates into the host cell\u2019s own genome. The host\u2019s cellular machinery then unknowingly transcribes viral mRNA for the rest of its life.

When we apply this classification system to animal viruses, we can organize the major viral families by their genome architecture.

Looking at the top half of the diagram, you can see the DNA viruses. Notice that almost all of them, from the adenoviruses to the herpesviruses, group into Baltimore Class I with double-stranded genomes. They rely heavily on the host nucleus for their replication machinery.

Now look at the bottom half of the diagram showing the RNA viruses. The structural diversity here is much wider. You can see the positive-sense single-stranded viruses grouped on the left, including the picornaviruses and coronaviruses. Because their genome functions immediately as mRNA, their replication cycle can occur entirely within the host cytoplasm without ever needing to enter the nucleus.

On the right side of the RNA section, we find the negative-sense single-stranded viruses, including the orthomyxoviruses like influenza. Because they must first transcribe their genome into a positive-sense format, their physical virion structure must be large enough to package and deliver those essential viral polymerases directly into the host cell upon infection.`,
    ei_percent: 90,
    ei_reasoning:
      "Understanding the basis of the Baltimore classification and the replication logic of all seven classes is highly testable across global medical curricula.",
  },
];

// ── Main Preview Page ─────────────────────────────────────────────────
export default function PreviewPage() {
  const [isMobile, setIsMobile] = useState(false);
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);

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
            V2 Preview
          </span>
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            Baltimore Classification System
          </span>
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
            <SlideCardGroup cards={TEST_SLIDES} onImageClick={setLightboxSrc} />
            <NarrativeSection section={TEST_TRANSCRIPT[0]} />
          </div>
        ) : (
          <div className="grid gap-8" style={{ gridTemplateColumns: "1fr 1fr" }}>
            <div className="space-y-4 sticky top-16 self-start">
              <SlideCardGroup cards={TEST_SLIDES} onImageClick={setLightboxSrc} />
            </div>
            <div className="pl-8 border-l" style={{ borderColor: "var(--border)" }}>
              <NarrativeSection section={TEST_TRANSCRIPT[0]} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
