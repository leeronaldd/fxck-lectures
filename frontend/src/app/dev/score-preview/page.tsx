"use client";

// Dev-only preview of ProfessorScoreCard without needing to sign in or run
// a real pipeline. Open http://localhost:PORT/dev/score-preview to see the
// card with mock transcript data.

import ProfessorScoreCard from "@/components/ProfessorScoreCard";
import type { TranscriptSection } from "@/lib/types";

// Mock transcript tuned to produce a ~31/100 overall score (bad professor).
// The ProfessorScoreCard computes scores from:
//   - ei_percent variance (clarity)
//   - section count (focus)
//   - narrative length (efficiency)
const mockTranscript: TranscriptSection[] = [
  {
    slide_number: 1,
    title: "Introduction to Bacteria",
    narrative:
      "Bacteria are single-celled prokaryotic organisms. They lack membrane-bound organelles and a true nucleus. " +
      "Before getting into the structure, it's worth noting that the professor spent almost 15 minutes on the history of microbiology, including a detailed anecdote about Leeuwenhoek's homemade lens. " +
      "We've re-explained the actual material from scratch below. ".repeat(10),
    ei_percent: 85,
    ei_reasoning: "Core exam content",
  },
  {
    slide_number: 2,
    title: "Cell Wall Basics",
    narrative:
      "The cell wall surrounds the cell membrane and provides structural integrity. " +
      "Think of it like a suit of armour. ".repeat(8),
    ei_percent: 92,
    ei_reasoning: "High exam importance",
  },
  {
    slide_number: 3,
    title: "Gram Staining (tangent)",
    narrative:
      "Your professor spent a while on the history of Hans Christian Gram. " +
      "The actual mechanism: crystal violet enters both gram-positive and gram-negative cells... ".repeat(6),
    ei_percent: 22,
    ei_reasoning: "Mostly historical tangent",
  },
  {
    slide_number: 4,
    title: "Peptidoglycan Structure",
    narrative:
      "Peptidoglycan is a mesh-like polymer of sugars and amino acids. Key exam fact: NAM-NAG-NAM-NAG alternating chains. ".repeat(7),
    ei_percent: 95,
    ei_reasoning: "Critical exam content",
  },
  {
    slide_number: 5,
    title: "Random aside on antibiotics discovery",
    narrative:
      "The professor went on about Fleming's penicillin discovery for a while. We condensed this. ".repeat(3),
    ei_percent: 15,
    ei_reasoning: "Low exam value — historical story",
  },
  {
    slide_number: 6,
    title: "Bacterial Capsules",
    narrative:
      "Capsules are slippery outer layers that help bacteria evade the immune system. Think: Teflon coating on a pan — your immune cells can't grab on. ".repeat(6),
    ei_percent: 78,
    ei_reasoning: "Exam-important",
  },
  {
    slide_number: 7,
    title: "Flagella and motility",
    narrative:
      "Some bacteria swim using a rotating tail called a flagellum. It's powered by a proton gradient and acts like a propeller. ".repeat(5),
    ei_percent: 60,
    ei_reasoning: "Moderate importance",
  },
  {
    slide_number: 8,
    title: "Fimbriae vs Pili (confused slide)",
    narrative:
      "The professor kept switching between the terms 'fimbriae' and 'pili' as if they were the same. They're not quite. We clarified below. ".repeat(7),
    ei_percent: 45,
    ei_reasoning: "Needs clarification",
  },
  {
    slide_number: 9,
    title: "Endospores",
    narrative:
      "Some bacteria (Bacillus, Clostridium) form endospores — dormant survival forms that resist heat, dehydration, and chemicals. ".repeat(6),
    ei_percent: 88,
    ei_reasoning: "High exam value",
  },
  {
    slide_number: 10,
    title: "Bacterial genetics recap",
    narrative:
      "Bacteria have a single circular chromosome plus optional plasmids. Plasmids carry extra genes — often antibiotic resistance. ".repeat(5),
    ei_percent: 72,
    ei_reasoning: "Core exam topic",
  },
];

export default function ScorePreviewPage() {
  return (
    <div
      className="min-h-screen py-12 px-4"
      style={{ background: "var(--bg)" }}
    >
      <div className="max-w-2xl mx-auto">
        <div className="mb-8 text-center">
          <h1
            className="text-2xl font-bold mb-2"
            style={{ color: "var(--text-primary)" }}
          >
            Professor Score Card — dev preview
          </h1>
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
            Click <strong>Preview</strong> to open the shareable PNG, or{" "}
            <strong>Share</strong> to trigger Web Share API / clipboard fallback.
          </p>
        </div>
        <ProfessorScoreCard
          transcript={mockTranscript}
          sessionName="Microbiology Lecture 3"
        />
      </div>
    </div>
  );
}
