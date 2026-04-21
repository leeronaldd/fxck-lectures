"use client";

import { useEffect, useRef, useState } from "react";

// ──────────────────────────────────────────────────────────────────────────
// "How does Klare work?" — 5-act scroll-triggered animation
// Pure CSS/SVG, no external animation dependency. Each act becomes active
// when it enters the viewport; sub-animations auto-loop while visible.
// ──────────────────────────────────────────────────────────────────────────

export default function HowKlareWorks() {
  return (
    <section id="how-klare-works" className="pb-24 pt-4 relative">
      <div className="text-center mb-16">
        <h2
          className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight leading-[1.1]"
          style={{ color: "var(--text-primary)" }}
        >
          How does <span className="gradient-text">Klare</span> work?
        </h2>
      </div>

      <div className="space-y-6 sm:space-y-10">
        <Act
          n={1}
          title="Transcribe Lecture to transcript"
          scene={<TranscribeScene />}
          flip={false}
        />
        <Connector />
        <Act
          n={2}
          title={
            <>
              Analyze Difficulty + Exam Importance,
              <br />
              and decide how deep it should explain each topic
            </>
          }
          scene={<PlanScene />}
          flip={true}
        />
        <Connector />
        <Act
          n={3}
          title={
            <>
              Custom Trained LLM
              <br />
              to Match Organic Chemistry Tutor Quality
            </>
          }
          scene={<TrainScene />}
          flip={false}
        />
        <Connector />
        <Act
          n={4}
          title="Scan for Missing Topics + Fact-check every claim against OpenStax and NCBI textbooks"
          scene={<FactCheckScene />}
          flip={true}
        />
      </div>

      <GlobalStyles />
    </section>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Act card — alternates scene/text left/right. Detects in-view to trigger
// its entry animation and unpause its sub-animation loops.
// ──────────────────────────────────────────────────────────────────────────

function Act({
  n,
  title,
  caption,
  desc,
  scene,
  flip,
}: {
  n: number;
  title: React.ReactNode;
  caption?: string;
  desc?: string;
  scene: React.ReactNode;
  flip: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setActive(true);
      },
      { threshold: 0.25, rootMargin: "0px 0px -10% 0px" }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      data-active={active}
      className="act-card relative"
      style={{
        opacity: active ? 1 : 0,
        transform: active ? "translateY(0)" : "translateY(30px)",
        transition:
          "opacity 0.7s cubic-bezier(0.22, 1, 0.36, 1), transform 0.7s cubic-bezier(0.22, 1, 0.36, 1)",
      }}
    >
      <div
        className={`glass rounded-2xl overflow-hidden grid grid-cols-1 lg:grid-cols-2 ${
          flip ? "lg:[&>div:first-child]:order-2" : ""
        }`}
        style={{ borderColor: "var(--border-glass)" }}
      >
        {/* Scene side */}
        <div
          className="relative overflow-hidden flex items-center justify-center"
          style={{
            background:
              "linear-gradient(135deg, rgba(255,107,53,0.06), rgba(139,92,246,0.04))",
            minHeight: 280,
          }}
        >
          <div className="w-full max-w-md p-6 sm:p-8">{scene}</div>
        </div>

        {/* Text side */}
        <div className="p-6 sm:p-10 flex flex-col justify-center">
          <div className="inline-flex items-center gap-2 mb-4 w-fit">
            <div
              className="w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold"
              style={{
                background: "var(--accent)",
                color: "#fff",
                boxShadow: "0 4px 12px var(--accent-glow)",
              }}
            >
              {n}
            </div>
            {caption && (
              <span
                className="text-[11px] font-semibold uppercase tracking-wider"
                style={{ color: "var(--accent)" }}
              >
                {caption}
              </span>
            )}
          </div>
          <h3
            className={`font-bold leading-tight ${
              desc ? "text-xl sm:text-2xl mb-3" : "text-xl sm:text-2xl"
            }`}
            style={{ color: "var(--text-primary)" }}
          >
            {title}
          </h3>
          {desc && (
            <p
              className="text-sm sm:text-[15px] leading-relaxed"
              style={{ color: "var(--text-secondary)" }}
            >
              {desc}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Vertical connector — dashed line with a pulse travelling down
// ──────────────────────────────────────────────────────────────────────────

function Connector() {
  return (
    <div className="flex justify-center" aria-hidden>
      <div className="connector-line relative" style={{ height: 40, width: 2 }}>
        <div
          className="absolute inset-0"
          style={{
            background:
              "repeating-linear-gradient(to bottom, var(--border) 0, var(--border) 4px, transparent 4px, transparent 8px)",
          }}
        />
        <div className="connector-pulse absolute left-1/2 -translate-x-1/2" />
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Shared primitives — cute bot character reused across scenes
// ──────────────────────────────────────────────────────────────────────────

type BotVariant = "default" | "gold" | "coach";

function Bot({
  x,
  y,
  scale = 1,
  variant = "default",
  eyeBlink = false,
  className,
}: {
  x: number;
  y: number;
  scale?: number;
  variant?: BotVariant;
  eyeBlink?: boolean;
  className?: string;
}) {
  const bodyColor =
    variant === "gold" || variant === "coach" ? "#F5B800" : "var(--accent)";
  const bodyStroke =
    variant === "gold" || variant === "coach" ? "#B88A00" : "#C84A1A";
  return (
    <g
      transform={`translate(${x} ${y}) scale(${scale})`}
      className={className}
    >
      {/* Antenna */}
      <line x1="0" y1="-10" x2="0" y2="-22" stroke="#3a3a3a" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="0" cy="-26" r="3.5" fill={bodyColor} />

      {/* Head */}
      <rect x="-22" y="-10" width="44" height="34" rx="10" fill="#FFFFFF" stroke="#2a2a2a" strokeWidth="1.5" />

      {/* Cheek blush */}
      <circle cx="-12" cy="12" r="3" fill="#FFB3A0" opacity="0.7" />
      <circle cx="12" cy="12" r="3" fill="#FFB3A0" opacity="0.7" />

      {/* Eyes */}
      <g className={eyeBlink ? "bot-eyes-blink" : ""}>
        <circle cx="-8" cy="4" r="2.6" fill="#1a1a1a" />
        <circle cx="8" cy="4" r="2.6" fill="#1a1a1a" />
        <circle cx="-7" cy="3" r="0.9" fill="#fff" />
        <circle cx="9" cy="3" r="0.9" fill="#fff" />
      </g>

      {/* Mouth — subtle smile */}
      <path d="M -5 14 Q 0 17 5 14" stroke="#1a1a1a" strokeWidth="1.5" fill="none" strokeLinecap="round" />

      {/* Body */}
      <rect x="-26" y="26" width="52" height="38" rx="10" fill={bodyColor} stroke={bodyStroke} strokeWidth="1.5" />

      {/* Body detail — orange brand circle on chest */}
      <circle cx="0" cy="45" r="6" fill="#fff" opacity="0.35" />
      <text x="0" y="49" textAnchor="middle" fontSize="8" fontWeight="700" fill={bodyStroke}>
        K
      </text>

      {/* Coach extras: whistle */}
      {variant === "coach" && (
        <g>
          <line x1="-18" y1="28" x2="10" y2="42" stroke="#888" strokeWidth="1" />
          <rect x="7" y="39" width="10" height="7" rx="2" fill="#e0e0e0" stroke="#888" strokeWidth="1" />
        </g>
      )}
    </g>
  );
}

function BotArm({
  x,
  y,
  side,
  className,
}: {
  x: number;
  y: number;
  side: "left" | "right";
  className?: string;
}) {
  const sign = side === "left" ? -1 : 1;
  return (
    <rect
      x={x + sign * 22}
      y={y + 30}
      width="7"
      height="22"
      rx="3.5"
      fill="var(--accent)"
      stroke="#C84A1A"
      strokeWidth="1"
      className={className}
    />
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Scene 1 — Transcribe: bot with headphones types; transcript + film roll
// ──────────────────────────────────────────────────────────────────────────

function TranscribeScene() {
  return (
    <svg viewBox="0 0 400 300" className="w-full h-auto">
      <defs>
        <linearGradient id="receipt-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#fff" />
          <stop offset="1" stopColor="#f3f3f3" />
        </linearGradient>
        <linearGradient id="video-screen" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#1e293b" />
          <stop offset="1" stopColor="#0f172a" />
        </linearGradient>
      </defs>

      {/* Incoming lecture — video player wooshing in from left */}
      <g className="lecture-woosh">
        <g transform="translate(50 115)">
          {/* Video frame */}
          <rect x="-26" y="-20" width="52" height="36" rx="4" fill="#0f172a" stroke="#334155" strokeWidth="1.5" />
          <rect x="-24" y="-18" width="48" height="32" rx="2" fill="url(#video-screen)" />
          {/* Pretend video content — a "professor" silhouette */}
          <circle cx="-8" cy="-4" r="4" fill="#64748b" opacity="0.7" />
          <path d="M -14 10 Q -8 2 -2 10 Z" fill="#64748b" opacity="0.7" />
          {/* Slide area beside professor */}
          <rect x="2" y="-10" width="18" height="12" rx="1" fill="#1e293b" stroke="#475569" strokeWidth="0.6" />
          <rect x="4" y="-8" width="10" height="1.2" fill="var(--accent)" opacity="0.8" />
          <rect x="4" y="-5" width="14" height="0.8" fill="#94a3b8" />
          <rect x="4" y="-3" width="12" height="0.8" fill="#94a3b8" />
          {/* Play triangle overlay */}
          <circle cx="0" cy="-2" r="7" fill="rgba(255,107,53,0.9)" />
          <path d="M -2 -5 L -2 1 L 3 -2 Z" fill="#fff" />
          {/* Progress bar */}
          <rect x="-22" y="11" width="44" height="1.5" rx="0.5" fill="#334155" />
          <rect x="-22" y="11" width="18" height="1.5" rx="0.5" fill="var(--accent)" />
          {/* "LECTURE.MP4" label under video */}
          <text x="0" y="24" textAnchor="middle" fontSize="6" fill="var(--text-muted)" fontWeight="700" letterSpacing="0.5">
            LECTURE.MP4
          </text>
        </g>
      </g>

      {/* Soundwave arcs entering bot's ear */}
      <g className="soundwave-pulse">
        <circle cx="115" cy="115" r="5" fill="none" stroke="var(--accent)" strokeWidth="1.5" opacity="0.9" />
        <circle cx="115" cy="115" r="10" fill="none" stroke="var(--accent)" strokeWidth="1.5" opacity="0.55" />
        <circle cx="115" cy="115" r="15" fill="none" stroke="var(--accent)" strokeWidth="1.5" opacity="0.3" />
      </g>

      {/* The bot — center, wearing headphones, sitting at typewriter */}
      <g transform="translate(180 95)">
        {/* Headphone band */}
        <path d="M -25 -6 Q 0 -28 25 -6" stroke="#2a2a2a" strokeWidth="3" fill="none" strokeLinecap="round" />
        <rect x="-32" y="-4" width="10" height="16" rx="3" fill="#2a2a2a" />
        <rect x="22" y="-4" width="10" height="16" rx="3" fill="#2a2a2a" />
        <circle cx="-27" cy="4" r="2" fill="var(--accent)" />
        <circle cx="27" cy="4" r="2" fill="var(--accent)" />

        <Bot x={0} y={0} eyeBlink />

        {/* Arms reaching down to typewriter keys */}
        <g className="typing-arm-left">
          <rect x="-24" y="52" width="8" height="20" rx="4" fill="var(--accent)" stroke="#C84A1A" strokeWidth="1" />
        </g>
        <g className="typing-arm-right">
          <rect x="16" y="52" width="8" height="20" rx="4" fill="var(--accent)" stroke="#C84A1A" strokeWidth="1" />
        </g>
      </g>

      {/* Typewriter — sits in front of bot */}
      <g transform="translate(180 175)">
        {/* Paper going up through platen — base of the receipt */}
        <rect x="-20" y="-50" width="40" height="60" fill="url(#receipt-grad)" stroke="#d4d4d4" strokeWidth="0.8" />

        {/* Main body */}
        <rect x="-52" y="0" width="104" height="40" rx="6" fill="#1f2937" stroke="#0f172a" strokeWidth="1.5" />
        {/* Front keys panel */}
        <rect x="-44" y="24" width="88" height="14" rx="3" fill="#111827" />
        {/* Individual keys */}
        {Array.from({ length: 8 }).map((_, i) => (
          <circle key={i} cx={-38 + i * 11} cy="31" r="2.2" fill="#374151" stroke="#1f2937" strokeWidth="0.5" />
        ))}
        {/* Space bar */}
        <rect x="-18" y="36" width="36" height="3" rx="1" fill="#374151" />

        {/* Platen (the roller paper wraps around) */}
        <rect x="-32" y="-8" width="64" height="10" rx="5" fill="#0f172a" stroke="#000" strokeWidth="0.8" />
        <rect x="-32" y="-8" width="64" height="3" rx="1.5" fill="#1f2937" />
        {/* Platen knobs */}
        <circle cx="-36" cy="-3" r="4" fill="#374151" stroke="#0f172a" strokeWidth="0.8" />
        <circle cx="36" cy="-3" r="4" fill="#374151" stroke="#0f172a" strokeWidth="0.8" />

        {/* Type bar striking the paper — animates */}
        <g className="typebar">
          <rect x="-1.5" y="-12" width="3" height="14" rx="1" fill="#6b7280" />
          <rect x="-3" y="-14" width="6" height="3" rx="0.5" fill="#374151" />
        </g>

        {/* KLARE brand plate on typewriter */}
        <rect x="-12" y="8" width="24" height="8" rx="1.5" fill="var(--accent)" />
        <text x="0" y="14" textAnchor="middle" fontSize="6" fontWeight="800" fill="#fff">
          KLARE
        </text>

        {/* Little ding bell on top right */}
        <circle cx="44" cy="-14" r="5" fill="#facc15" stroke="#ca8a04" strokeWidth="0.8" />
        <circle cx="44" cy="-14" r="1.5" fill="#ca8a04" />
      </g>

      {/* Transcript strip — emerges from right side of typewriter platen, hangs down */}
      <g transform="translate(232 160)">
        <g className="receipt-unroll">
          <rect x="0" y="0" width="38" height="130" fill="url(#receipt-grad)" stroke="#d4d4d4" strokeWidth="0.8" />
          {/* Typed text lines — varied widths for a realistic typed look */}
          {Array.from({ length: 22 }).map((_, i) => (
            <rect
              key={i}
              x={4 + (i % 3) * 0.4}
              y={6 + i * 5.5}
              width={26 - ((i * 5) % 14)}
              height="1.6"
              rx="0.5"
              fill="#1a1a1a"
              opacity="0.7"
            />
          ))}
          {/* Jagged torn bottom */}
          <path
            d="M 0 130 L 4 126 L 8 130 L 12 126 L 16 130 L 20 126 L 24 130 L 28 126 L 32 130 L 36 126 L 38 130 Z"
            fill="url(#receipt-grad)"
            stroke="#d4d4d4"
            strokeWidth="0.8"
          />
        </g>
      </g>

      {/* "Ding!" sparkle near the bell when the typebar strikes */}
      <g className="ding-sparkle" transform="translate(228 153)">
        <path d="M 0 -6 L 1.5 -1.5 L 6 0 L 1.5 1.5 L 0 6 L -1.5 1.5 L -6 0 L -1.5 -1.5 Z" fill="#facc15" />
      </g>
    </svg>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Scene 2 — Plan: bot stamps topic cards with DEEP/SKIM + EI%
// ──────────────────────────────────────────────────────────────────────────

function PlanScene() {
  // Three papers cycle through the belt, each getting a different EI score.
  // Each paper runs an 18s full cycle (6s visible, 12s hidden), staggered 6s.
  // Inside its visible window: enter → scan → stamp → reveal → exit.
  const papers = [
    { score: "85%", delay: "0s" },
    { score: "62%", delay: "-12s" },
    { score: "91%", delay: "-6s" },
  ];

  return (
    <svg viewBox="0 0 400 300" className="w-full h-auto">
      <defs>
        <linearGradient id="belt-surface" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#1f2937" />
          <stop offset="0.5" stopColor="#111827" />
          <stop offset="1" stopColor="#1f2937" />
        </linearGradient>
        <linearGradient id="rail-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#334155" />
          <stop offset="1" stopColor="#0f172a" />
        </linearGradient>
      </defs>

      {/* Bird's-eye conveyor belt — flat surface facing the viewer */}
      <rect x="0" y="95" width="400" height="115" fill="url(#belt-surface)" />
      {/* Belt side rails (edges of the conveyor) */}
      <rect x="0" y="92" width="400" height="5" fill="url(#rail-grad)" />
      <rect x="0" y="208" width="400" height="5" fill="url(#rail-grad)" />

      {/* Scrolling belt markings — horizontal chevrons slide left to imply motion */}
      <g className="belt-scroll-bev">
        {Array.from({ length: 12 }).map((_, i) => (
          <g key={i}>
            <rect x={i * 40} y="100" width="18" height="2.5" fill="#374151" opacity="0.7" />
            <rect x={i * 40} y="204" width="18" height="2.5" fill="#374151" opacity="0.7" />
            <rect x={i * 40} y="150" width="22" height="5" rx="1" fill="#1f2937" />
          </g>
        ))}
      </g>

      {/* PAPERS — three cycle through the belt, each with its own EI score.
          Uses a --delay CSS var that cascades to paper-cycle-bev, scan-beam,
          and stamp-reveal so they all stay in phase. */}
      {papers.map((p, i) => (
        <g
          key={i}
          className="paper-cycle-bev"
          style={{ "--delay": p.delay } as React.CSSProperties}
        >
          <g transform="translate(110 112)">
            {/* Paper body */}
            <rect x="0" y="0" width="180" height="86" rx="2" fill="#fff" stroke="#d4d4d4" strokeWidth="0.8" />

            {/* "TOPIC" label — kept on the left, clear of the stamp area */}
            <rect x="10" y="10" width="18" height="3" rx="0.5" fill="var(--accent)" />
            <rect x="32" y="10" width="50" height="3" rx="0.5" fill="#111827" />
            {/* Subject lines — only on the LEFT half, so stamp reveals on the
                right side sit on clean white paper (no lines behind the score). */}
            <rect x="10" y="20" width="90" height="1.8" rx="0.5" fill="#6b7280" />
            <rect x="10" y="26" width="78" height="1.8" rx="0.5" fill="#6b7280" />
            <rect x="10" y="50" width="88" height="1.5" rx="0.5" fill="#9ca3af" />
            <rect x="10" y="56" width="80" height="1.5" rx="0.5" fill="#9ca3af" />
            <rect x="10" y="62" width="92" height="1.5" rx="0.5" fill="#9ca3af" />
            <rect x="10" y="68" width="72" height="1.5" rx="0.5" fill="#9ca3af" />
            <rect x="10" y="74" width="84" height="1.5" rx="0.5" fill="#9ca3af" />

            {/* SCAN BEAM — vertical orange highlight that sweeps L→R over paper */}
            <g
              className="scan-beam"
              style={{ "--delay": p.delay } as React.CSSProperties}
            >
              <rect x="-3" y="-4" width="6" height="94" fill="var(--accent)" opacity="0.75" />
              <rect x="-8" y="-4" width="16" height="94" fill="var(--accent)" opacity="0.15" />
            </g>

            {/* STAMP REVEAL — "Exam Importance Score: XX%" stamped at top-right.
                Larger box + readable label across two lines. */}
            <g
              className="stamp-reveal"
              style={{ "--delay": p.delay } as React.CSSProperties}
            >
              <g transform="translate(124 36) rotate(-4)">
                {/* Inked border — rubber stamp effect */}
                <rect
                  x="-54"
                  y="-26"
                  width="108"
                  height="50"
                  rx="3"
                  fill="rgba(255, 107, 53, 0.1)"
                  stroke="var(--accent)"
                  strokeWidth="2"
                />
                {/* Label — two lines, larger type */}
                <text x="0" y="-13" textAnchor="middle" fontSize="8.5" fontWeight="800" fill="var(--accent)" letterSpacing="0.3">
                  EXAM IMPORTANCE
                </text>
                <text x="0" y="-4" textAnchor="middle" fontSize="7.5" fontWeight="700" fill="var(--accent)" letterSpacing="0.5">
                  SCORE
                </text>
                {/* Divider between label and score */}
                <line x1="-48" y1="1" x2="48" y2="1" stroke="var(--accent)" strokeWidth="1" opacity="0.55" />
                {/* Score */}
                <text x="0" y="19" textAnchor="middle" fontSize="18" fontWeight="900" fill="var(--accent)">
                  {p.score}
                </text>
              </g>
            </g>
          </g>
        </g>
      ))}

      {/* ROBOTIC ARM — bird's-eye view, enters from the right.
          The whole arm translates out to the right during the "reveal" phase
          so the stamped EI% on the paper is visible. The stamp tool inside
          also animates (scan-wobble + press-down). */}
      <g className="arm-extend-retract">
        {/* Shoulder joint — at right edge of scene */}
        <circle cx="398" cy="155" r="20" fill="var(--accent)" stroke="#C84A1A" strokeWidth="1.5" />
        <circle cx="393" cy="150" r="4" fill="#fff" opacity="0.3" />
        {/* Upper arm — horizontal from shoulder */}
        <rect x="340" y="143" width="62" height="24" rx="11" fill="var(--accent)" stroke="#C84A1A" strokeWidth="1.5" />
        {/* Elbow joint */}
        <circle cx="340" cy="155" r="15" fill="var(--accent)" stroke="#C84A1A" strokeWidth="1.5" />
        {/* Forearm — angled slightly up toward paper's top-right corner */}
        <g transform="translate(340 155) rotate(-18)">
          <rect x="-58" y="-10" width="58" height="20" rx="9" fill="var(--accent)" stroke="#C84A1A" strokeWidth="1.5" />
        </g>
        {/* Wrist joint */}
        <circle cx="285" cy="137" r="11" fill="var(--accent)" stroke="#C84A1A" strokeWidth="1.5" />

        {/* The stamp tool — has its own animation for scan-wobble + press */}
        <g className="arm-stamp-tool">
          {/* Wooden handle (top-down view) */}
          <rect x="277" y="120" width="16" height="16" rx="2" fill="#92400e" stroke="#451a03" strokeWidth="0.8" />
          <rect x="277" y="120" width="16" height="4" rx="1" fill="#b45309" />
          {/* Stamp body (wider base that meets paper) */}
          <rect x="270" y="134" width="30" height="10" rx="1.5" fill="#0f172a" stroke="#000" strokeWidth="0.8" />
          {/* Stamp face (the inked pad) */}
          <rect x="272" y="137" width="26" height="5" rx="1" fill="var(--accent)" />

          {/* Impact shadow ring — appears at the moment of stamping */}
          <g className="stamp-impact-ring">
            <ellipse cx="285" cy="142" rx="26" ry="7" fill="none" stroke="var(--accent)" strokeWidth="1.8" opacity="0.85" />
          </g>
        </g>
      </g>
    </svg>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Scene 3 — Train: bot does handstand pushups, gold coach holds playbook
// ──────────────────────────────────────────────────────────────────────────

function TrainScene() {
  return (
    <svg viewBox="0 0 400 300" className="w-full h-auto">
      <defs>
        <linearGradient id="gym-wall" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#374151" />
          <stop offset="1" stopColor="#1f2937" />
        </linearGradient>
        <linearGradient id="gym-floor" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#1a1a1a" />
          <stop offset="1" stopColor="#0f0f0f" />
        </linearGradient>
        <pattern id="rubber-tiles" x="0" y="0" width="16" height="16" patternUnits="userSpaceOnUse">
          <rect width="16" height="16" fill="#111827" />
          <circle cx="4" cy="4" r="1" fill="#1f2937" />
          <circle cx="12" cy="4" r="1" fill="#1f2937" />
          <circle cx="4" cy="12" r="1" fill="#1f2937" />
          <circle cx="12" cy="12" r="1" fill="#1f2937" />
        </pattern>
      </defs>

      {/* Gym back wall */}
      <rect x="0" y="0" width="400" height="210" fill="url(#gym-wall)" />

      {/* Horizon line — where wall meets floor */}
      <rect x="0" y="208" width="400" height="2" fill="#0f172a" />

      {/* Rubber-tile gym floor */}
      <rect x="0" y="210" width="400" height="90" fill="url(#rubber-tiles)" />

      {/* Wall-mounted barbell rack — back left */}
      <g transform="translate(40 70)">
        {/* Rack uprights */}
        <rect x="0" y="0" width="4" height="130" fill="#475569" />
        <rect x="80" y="0" width="4" height="130" fill="#475569" />
        {/* Horizontal hooks */}
        {[25, 70, 115].map((y, i) => (
          <g key={i}>
            <rect x="-6" y={y} width="10" height="3" rx="1" fill="#64748b" />
            <rect x="80" y={y} width="10" height="3" rx="1" fill="#64748b" />
            {/* Barbell on hook */}
            <rect x="4" y={y - 2} width="76" height="7" rx="1" fill="#94a3b8" />
            {/* Weight plates */}
            <rect x="-2" y={y - 6} width="8" height="15" rx="1" fill="#0f172a" stroke="#475569" strokeWidth="0.8" />
            <rect x="78" y={y - 6} width="8" height="15" rx="1" fill="#0f172a" stroke="#475569" strokeWidth="0.8" />
          </g>
        ))}
      </g>

      {/* Wall clock — upper center back */}
      <g transform="translate(200 55)">
        <circle cx="0" cy="0" r="20" fill="#f3f4f6" stroke="#1f2937" strokeWidth="2" />
        <circle cx="0" cy="0" r="20" fill="none" stroke="#e5e7eb" strokeWidth="0.5" />
        {/* Hour markers — precomputed + rounded to avoid SSR/client FP drift */}
        {[
          [0, -15, 0, -17],
          [7.5, -13, 8.5, -14.72],
          [13, -7.5, 14.72, -8.5],
          [15, 0, 17, 0],
          [13, 7.5, 14.72, 8.5],
          [7.5, 13, 8.5, 14.72],
          [0, 15, 0, 17],
          [-7.5, 13, -8.5, 14.72],
          [-13, 7.5, -14.72, 8.5],
          [-15, 0, -17, 0],
          [-13, -7.5, -14.72, -8.5],
          [-7.5, -13, -8.5, -14.72],
        ].map(([x1, y1, x2, y2], i) => (
          <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#1f2937" strokeWidth="1.2" />
        ))}
        {/* Hour hand */}
        <line x1="0" y1="0" x2="0" y2="-9" stroke="#1f2937" strokeWidth="2" strokeLinecap="round" className="clock-hour" />
        {/* Minute hand */}
        <line x1="0" y1="0" x2="6" y2="-13" stroke="#1f2937" strokeWidth="1.5" strokeLinecap="round" className="clock-min" />
        <circle cx="0" cy="0" r="1.5" fill="var(--accent)" />
      </g>

      {/* Motivational poster — upper right */}
      <g transform="translate(300 50)">
        <rect x="0" y="0" width="70" height="80" rx="2" fill="#fff" stroke="#1f2937" strokeWidth="1.5" />
        <rect x="4" y="4" width="62" height="52" rx="1" fill="var(--accent)" />
        <text x="35" y="22" textAnchor="middle" fontSize="8" fontWeight="800" fill="#fff">
          NO
        </text>
        <text x="35" y="32" textAnchor="middle" fontSize="8" fontWeight="800" fill="#fff">
          PAIN
        </text>
        <text x="35" y="42" textAnchor="middle" fontSize="8" fontWeight="800" fill="#fff">
          NO
        </text>
        <text x="35" y="52" textAnchor="middle" fontSize="8" fontWeight="800" fill="#fff">
          GAIN
        </text>
        <text x="35" y="66" textAnchor="middle" fontSize="5" fontWeight="700" fill="#1f2937" letterSpacing="0.5">
          KLARE GYM
        </text>
        <rect x="14" y="72" width="42" height="2" rx="0.5" fill="#6b7280" />
      </g>

      {/* Dumbbells scattered on floor — back right */}
      <g transform="translate(260 235)">
        {/* Large dumbbell */}
        <rect x="0" y="0" width="40" height="5" rx="1" fill="#94a3b8" />
        <rect x="-4" y="-4" width="8" height="13" rx="1" fill="#0f172a" stroke="#475569" strokeWidth="0.8" />
        <rect x="36" y="-4" width="8" height="13" rx="1" fill="#0f172a" stroke="#475569" strokeWidth="0.8" />
        {/* Smaller dumbbell behind */}
        <rect x="50" y="2" width="24" height="4" rx="1" fill="#94a3b8" />
        <rect x="47" y="-1" width="6" height="10" rx="1" fill="#0f172a" stroke="#475569" strokeWidth="0.8" />
        <rect x="71" y="-1" width="6" height="10" rx="1" fill="#0f172a" stroke="#475569" strokeWidth="0.8" />
      </g>

      {/* Single dumbbell by the bot, left */}
      <g transform="translate(45 265)">
        <rect x="0" y="0" width="32" height="4" rx="1" fill="#94a3b8" />
        <rect x="-3" y="-3" width="6" height="10" rx="1" fill="var(--accent)" stroke="#C84A1A" strokeWidth="0.8" />
        <rect x="29" y="-3" width="6" height="10" rx="1" fill="var(--accent)" stroke="#C84A1A" strokeWidth="0.8" />
        <text x="16" y="3" textAnchor="middle" fontSize="3.5" fontWeight="800" fill="#1f2937">
          20KG
        </text>
      </g>

      {/* The pushup bot — true leverage/lever motion.
          Anchors: FRONT HAND (14, 53) and LEG TAIL (140, 50) both stay
          planted on the ground across both poses. Body raised clearly
          OFF the ground in UP pose so it reads as "elevated plank doing
          pushup" — not "lying down". Head tilted forward (chin-toward-
          floor) reinforces the active pushup pose. */}
      <g transform="translate(130 215)">
        {/* Ground shadow (static) — wider/stronger to emphasize elevation */}
        <ellipse cx="65" cy="54" rx="85" ry="5" fill="#000" opacity="0.35" />

        {/* ============== UP POSE (body high, arm extended) ============== */}
        <g className="pushup-up">
          {/* BACK leg — rotates from planted tail (138, 50) up to hip (60, 13).
              Steeper angle (~28°) because body is higher now. */}
          <g transform="rotate(28 138 50)">
            <rect x="52" y="46" width="86" height="8" rx="4" fill="var(--accent)" stroke="#8a3414" strokeWidth="0.8" opacity="0.65" />
          </g>
          {/* BACK arm (dimmer) — straight vertical down to planted hand */}
          <rect x="6" y="11" width="8" height="40" rx="3" fill="var(--accent)" stroke="#8a3414" strokeWidth="0.8" opacity="0.65" />
          <circle cx="10" cy="51" r="5" fill="#fff" stroke="#2a2a2a" strokeWidth="0.8" opacity="0.8" />
          {/* BODY — horizontal plank, clearly elevated. Hip at right end (62, 13). */}
          <rect x="0" y="5" width="64" height="14" rx="5" fill="var(--accent)" stroke="#C84A1A" strokeWidth="1.3" />
          <circle cx="32" cy="12" r="4" fill="#fff" opacity="0.4" />
          <text x="32" y="15" textAnchor="middle" fontSize="5.5" fontWeight="800" fill="#C84A1A">K</text>
          <line x1="20" y1="12" x2="24" y2="12" stroke="#fff" strokeWidth="0.5" opacity="0.4" />
          <line x1="44" y1="12" x2="48" y2="12" stroke="#fff" strokeWidth="0.5" opacity="0.4" />
          {/* FRONT leg — planted tail (140, 50), hip at (62, 13). */}
          <g transform="rotate(28 140 50)">
            <rect x="54" y="45" width="86" height="10" rx="5" fill="var(--accent)" stroke="#C84A1A" strokeWidth="1" />
          </g>
          {/* HEAD — tilted 18° forward so face looks DOWN at ground (pushup form,
              not lying sideways). Pivot at the neck where head meets body. */}
          <g transform="rotate(18 0 12)">
            <rect x="-24" y="1" width="28" height="22" rx="7" fill="#fff" stroke="#2a2a2a" strokeWidth="1.3" />
            <line x1="-6" y1="1" x2="-12" y2="-6" stroke="#3a3a3a" strokeWidth="1.3" strokeLinecap="round" />
            <circle cx="-13" cy="-7" r="2.5" fill="var(--accent)" />
            {/* Eyes squinted (exertion) */}
            <path d="M -18 9 Q -15 11.5 -12 9" stroke="#1a1a1a" strokeWidth="1.3" fill="none" strokeLinecap="round" />
            <path d="M -8 9 Q -5 11.5 -2 9" stroke="#1a1a1a" strokeWidth="1.3" fill="none" strokeLinecap="round" />
            <circle cx="-15" cy="15" r="2" fill="#FFB3A0" opacity="0.75" />
            {/* Gritted teeth */}
            <rect x="-10" y="15" width="11" height="3" rx="0.5" fill="#2a2a2a" />
            <line x1="-7" y1="15" x2="-7" y2="18" stroke="#fff" strokeWidth="0.4" />
            <line x1="-4" y1="15" x2="-4" y2="18" stroke="#fff" strokeWidth="0.4" />
            <line x1="-1" y1="15" x2="-1" y2="18" stroke="#fff" strokeWidth="0.4" />
          </g>
          {/* FRONT arm — STRAIGHT vertical. Shoulder (14, 12) to hand (14, 53).
              Length 41 — long, clearly shows body is held UP off the ground. */}
          <g>
            <circle cx="14" cy="12" r="6" fill="var(--accent)" stroke="#C84A1A" strokeWidth="1" />
            <rect x="10" y="12" width="8" height="41" rx="3" fill="var(--accent)" stroke="#C84A1A" strokeWidth="1" />
            <circle cx="14" cy="53" r="6" fill="#fff" stroke="#2a2a2a" strokeWidth="1" />
            <line x1="10" y1="53" x2="18" y2="53" stroke="#2a2a2a" strokeWidth="0.4" opacity="0.5" />
          </g>
        </g>

        {/* ============== DOWN POSE ==============
            Body drops ~16px (chest toward ground). Leg tail stays at (140, 50);
            only the hip end swings down, so the leg is a flatter lever now.
            Front arm deeply bent. Head still tilted forward, face near ground. */}
        <g className="pushup-down">
          {/* BACK leg — hip at (60, 29), planted tail (138, 50). Flatter angle. */}
          <g transform="rotate(15 138 50)">
            <rect x="52" y="46" width="82" height="8" rx="4" fill="var(--accent)" stroke="#8a3414" strokeWidth="0.8" opacity="0.65" />
          </g>
          {/* BACK arm (dimmer) — BENT. Shoulder (10, 27), hand (10, 51). */}
          <g opacity="0.65">
            <g transform="rotate(-50 10 27)">
              <rect x="6" y="27" width="8" height="14" rx="3" fill="var(--accent)" stroke="#8a3414" strokeWidth="0.8" />
            </g>
            <circle cx="20" cy="37" r="4" fill="var(--accent)" stroke="#8a3414" strokeWidth="0.8" />
            <g transform="rotate(52 20 37)">
              <rect x="16" y="37" width="8" height="14" rx="3" fill="var(--accent)" stroke="#8a3414" strokeWidth="0.8" />
            </g>
          </g>
          <circle cx="10" cy="51" r="5" fill="#fff" stroke="#2a2a2a" strokeWidth="0.8" opacity="0.8" />
          {/* BODY — dropped ~16px. Hip at right end (62, 29). */}
          <rect x="0" y="21" width="64" height="14" rx="5" fill="var(--accent)" stroke="#C84A1A" strokeWidth="1.3" />
          <circle cx="32" cy="28" r="4" fill="#fff" opacity="0.4" />
          <text x="32" y="31" textAnchor="middle" fontSize="5.5" fontWeight="800" fill="#C84A1A">K</text>
          <line x1="20" y1="28" x2="24" y2="28" stroke="#fff" strokeWidth="0.5" opacity="0.4" />
          <line x1="44" y1="28" x2="48" y2="28" stroke="#fff" strokeWidth="0.5" opacity="0.4" />
          {/* FRONT leg — planted tail (140, 50), hip at (62, 29). Flatter angle. */}
          <g transform="rotate(15 140 50)">
            <rect x="54" y="45" width="82" height="10" rx="5" fill="var(--accent)" stroke="#C84A1A" strokeWidth="1" />
          </g>
          {/* HEAD — tilted forward even more (peak exertion, chin near ground) */}
          <g transform="rotate(22 0 28)">
            <rect x="-24" y="17" width="28" height="22" rx="7" fill="#fff" stroke="#2a2a2a" strokeWidth="1.3" />
            <line x1="-6" y1="17" x2="-14" y2="10" stroke="#3a3a3a" strokeWidth="1.3" strokeLinecap="round" />
            <circle cx="-15" cy="9" r="2.5" fill="var(--accent)" />
            <path d="M -18 25 Q -15 27 -12 25" stroke="#1a1a1a" strokeWidth="1.5" fill="none" strokeLinecap="round" />
            <path d="M -8 25 Q -5 27 -2 25" stroke="#1a1a1a" strokeWidth="1.5" fill="none" strokeLinecap="round" />
            <circle cx="-15" cy="31" r="2" fill="#FFB3A0" opacity="0.8" />
            <rect x="-10" y="31" width="11" height="3" rx="0.5" fill="#2a2a2a" />
            <line x1="-7" y1="31" x2="-7" y2="34" stroke="#fff" strokeWidth="0.4" />
            <line x1="-4" y1="31" x2="-4" y2="34" stroke="#fff" strokeWidth="0.4" />
            <line x1="-1" y1="31" x2="-1" y2="34" stroke="#fff" strokeWidth="0.4" />
          </g>
          {/* FRONT arm — DEEPLY BENT. Shoulder (14, 28), elbow at (26, 40),
              forearm back to planted hand at (14, 53). */}
          <g>
            <circle cx="14" cy="28" r="6" fill="var(--accent)" stroke="#C84A1A" strokeWidth="1" />
            <g transform="rotate(-50 14 28)">
              <rect x="10" y="28" width="8" height="15" rx="3" fill="var(--accent)" stroke="#C84A1A" strokeWidth="1" />
            </g>
            <circle cx="26" cy="38" r="6" fill="var(--accent)" stroke="#C84A1A" strokeWidth="1.2" />
            <g transform="rotate(52 26 38)">
              <rect x="22" y="38" width="8" height="17" rx="3" fill="var(--accent)" stroke="#C84A1A" strokeWidth="1" />
            </g>
            <circle cx="14" cy="53" r="6" fill="#fff" stroke="#2a2a2a" strokeWidth="1" />
            <line x1="10" y1="53" x2="18" y2="53" stroke="#2a2a2a" strokeWidth="0.4" opacity="0.5" />
          </g>
        </g>
      </g>

      {/* Sweat drops — flying off the bot's head/forehead area */}
      <g className="sweat-drop sweat-1">
        <path d="M 112 225 Q 109 230 111 235 Q 115 232 115 228 Z" fill="#60a5fa" opacity="0.85" />
      </g>
      <g className="sweat-drop sweat-2">
        <path d="M 118 225 Q 115 230 117 235 Q 121 232 121 228 Z" fill="#60a5fa" opacity="0.7" />
      </g>

      {/* Effort / pump lines around the bot */}
      <g className="effort-lines">
        <line x1="100" y1="232" x2="92" y2="230" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" />
        <line x1="100" y1="242" x2="90" y2="242" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" />
        <line x1="100" y1="252" x2="92" y2="254" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" />
        <line x1="270" y1="232" x2="278" y2="230" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" />
        <line x1="270" y1="252" x2="278" y2="254" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" />
      </g>

    </svg>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Scene 4 — Fact-check: bot with magnifying glass + textbook, green checks
// ──────────────────────────────────────────────────────────────────────────

function FactCheckScene() {
  return (
    <svg viewBox="0 0 400 300" className="w-full h-auto">
      {/* The document being checked */}
      <g transform="translate(40 60)">
        <rect x="0" y="0" width="180" height="200" rx="4" fill="#fff" stroke="#d0d0d0" strokeWidth="1.2" />
        <rect x="12" y="14" width="80" height="5" rx="1" fill="var(--accent)" />
        <rect x="12" y="26" width="150" height="2" rx="1" fill="#888" />
        <rect x="12" y="32" width="135" height="2" rx="1" fill="#888" />
        <rect x="12" y="38" width="155" height="2" rx="1" fill="#888" />
        <rect x="12" y="44" width="120" height="2" rx="1" fill="#888" />

        <rect x="12" y="60" width="70" height="4" rx="1" fill="var(--accent)" opacity="0.7" />
        <rect x="12" y="70" width="150" height="2" rx="1" fill="#888" />
        <rect x="12" y="76" width="140" height="2" rx="1" fill="#888" />
        <rect x="12" y="82" width="155" height="2" rx="1" fill="#888" />

        <rect x="12" y="100" width="80" height="4" rx="1" fill="var(--accent)" opacity="0.7" />
        <rect x="12" y="110" width="145" height="2" rx="1" fill="#888" />
        <rect x="12" y="116" width="155" height="2" rx="1" fill="#888" />
        <rect x="12" y="122" width="125" height="2" rx="1" fill="#888" />

        <rect x="12" y="140" width="60" height="4" rx="1" fill="var(--accent)" opacity="0.7" />
        <rect x="12" y="150" width="150" height="2" rx="1" fill="#888" />
        <rect x="12" y="156" width="140" height="2" rx="1" fill="#888" />
        <rect x="12" y="162" width="120" height="2" rx="1" fill="#888" />

        {/* Green checkmark stamps dropping onto the doc */}
        <g className="check-stamp check-1">
          <circle cx="155" cy="32" r="10" fill="#22c55e" />
          <path d="M 150 32 L 154 36 L 160 28" stroke="#fff" strokeWidth="2.2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </g>
        <g className="check-stamp check-2">
          <circle cx="155" cy="76" r="10" fill="#22c55e" />
          <path d="M 150 76 L 154 80 L 160 72" stroke="#fff" strokeWidth="2.2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </g>
        <g className="check-stamp check-3">
          <circle cx="155" cy="116" r="10" fill="#22c55e" />
          <path d="M 150 116 L 154 120 L 160 112" stroke="#fff" strokeWidth="2.2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </g>
      </g>

      {/* Magnifying glass — sweeps across the document */}
      <g className="magnifier-sweep">
        <circle cx="0" cy="0" r="28" fill="rgba(255, 107, 53, 0.12)" stroke="var(--accent)" strokeWidth="3" />
        <circle cx="0" cy="0" r="22" fill="rgba(255, 255, 255, 0.25)" />
        {/* Handle */}
        <rect x="20" y="20" width="6" height="30" rx="3" fill="var(--accent)" stroke="#C84A1A" strokeWidth="1.2" transform="rotate(45 23 35)" />
        {/* Inner shine */}
        <circle cx="-8" cy="-8" r="6" fill="rgba(255, 255, 255, 0.4)" />
      </g>

      {/* The fact-check bot in the corner */}
      <g transform="translate(310 180)">
        <Bot x={0} y={0} scale={0.75} eyeBlink />
      </g>

      {/* OpenStax textbook — corner reference */}
      <g transform="translate(275 50)" className="textbook-float">
        {/* Book back cover shadow */}
        <rect x="2" y="2" width="80" height="100" rx="3" fill="#6b2a2a" />
        {/* Book front */}
        <rect x="0" y="0" width="80" height="100" rx="3" fill="#B32828" stroke="#6b2a2a" strokeWidth="1.5" />
        {/* Spine */}
        <rect x="0" y="0" width="6" height="100" fill="#8a1f1f" />
        {/* Title block */}
        <rect x="14" y="14" width="58" height="20" rx="1" fill="#fff" opacity="0.95" />
        <text x="43" y="24" textAnchor="middle" fontSize="8" fontWeight="800" fill="#B32828">
          OpenStax
        </text>
        <text x="43" y="31" textAnchor="middle" fontSize="5.5" fontWeight="600" fill="#8a1f1f">
          TEXTBOOK
        </text>
        {/* Emblem */}
        <circle cx="43" cy="60" r="12" fill="none" stroke="#fff" strokeWidth="1.5" opacity="0.8" />
        <path d="M 37 60 L 41 64 L 49 56" stroke="#fff" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" opacity="0.8" />
        <rect x="24" y="80" width="36" height="2" fill="#fff" opacity="0.5" />
        <rect x="30" y="86" width="24" height="1.5" fill="#fff" opacity="0.4" />
      </g>

      {/* Beam between textbook and doc — "cross-reference" */}
      <path
        d="M 290 100 Q 260 130 220 150"
        stroke="var(--accent)"
        strokeWidth="1.5"
        strokeDasharray="3 3"
        fill="none"
        opacity="0.5"
        className="reference-beam"
      />
    </svg>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Scene 5 — Output: factory produces a clean doc
// ──────────────────────────────────────────────────────────────────────────

function OutputScene() {
  return (
    <svg viewBox="0 0 400 300" className="w-full h-auto">
      {/* Factory building */}
      <g transform="translate(60 100)">
        {/* Main building */}
        <rect x="0" y="40" width="140" height="100" rx="4" fill="#3a3a3a" stroke="#1a1a1a" strokeWidth="1.5" />
        {/* Roof */}
        <polygon points="0,40 70,10 140,40" fill="#2a2a2a" stroke="#1a1a1a" strokeWidth="1.5" />
        {/* Chimney */}
        <rect x="100" y="0" width="16" height="25" fill="#2a2a2a" stroke="#1a1a1a" strokeWidth="1.5" />
        {/* Smoke puffs */}
        <g className="smoke-puffs">
          <circle cx="108" cy="-8" r="5" fill="#fff" opacity="0.3" className="smoke-1" />
          <circle cx="112" cy="-18" r="7" fill="#fff" opacity="0.2" className="smoke-2" />
          <circle cx="106" cy="-28" r="9" fill="#fff" opacity="0.15" className="smoke-3" />
        </g>
        {/* Factory windows — lit up */}
        <rect x="12" y="52" width="18" height="18" rx="1" fill="var(--accent)" opacity="0.9" className="window-flicker-1" />
        <rect x="38" y="52" width="18" height="18" rx="1" fill="var(--accent)" opacity="0.9" className="window-flicker-2" />
        <rect x="64" y="52" width="18" height="18" rx="1" fill="var(--accent)" opacity="0.9" className="window-flicker-3" />
        <rect x="90" y="52" width="18" height="18" rx="1" fill="var(--accent)" opacity="0.9" className="window-flicker-1" />
        <rect x="12" y="84" width="18" height="18" rx="1" fill="var(--accent)" opacity="0.6" className="window-flicker-2" />
        <rect x="38" y="84" width="18" height="18" rx="1" fill="var(--accent)" opacity="0.6" className="window-flicker-3" />

        {/* Factory door with output pipe */}
        <rect x="120" y="90" width="30" height="40" rx="2" fill="#1a1a1a" />
        <rect x="135" y="108" width="40" height="8" rx="2" fill="#2a2a2a" />

        {/* KLARE sign on factory */}
        <rect x="50" y="22" width="40" height="14" rx="2" fill="var(--accent)" />
        <text x="70" y="32" textAnchor="middle" fontSize="9" fontWeight="800" fill="#fff">
          KLARE
        </text>
      </g>

      {/* Clean document emerging from pipe */}
      <g className="output-doc" transform="translate(265 200)">
        <rect x="0" y="0" width="90" height="70" rx="3" fill="#fff" stroke="#d0d0d0" strokeWidth="1.2" />
        {/* Header bar */}
        <rect x="0" y="0" width="90" height="14" rx="3" fill="var(--accent)" />
        <rect x="0" y="10" width="90" height="4" fill="var(--accent)" />
        <text x="45" y="10" textAnchor="middle" fontSize="6" fontWeight="800" fill="#fff">
          YOUR LECTURE
        </text>

        {/* Content lines */}
        <rect x="6" y="20" width="32" height="2.5" rx="0.5" fill="var(--accent)" />
        <rect x="6" y="26" width="78" height="1.5" rx="0.5" fill="#888" />
        <rect x="6" y="30" width="70" height="1.5" rx="0.5" fill="#888" />
        <rect x="6" y="34" width="78" height="1.5" rx="0.5" fill="#888" />
        <rect x="6" y="38" width="60" height="1.5" rx="0.5" fill="#888" />

        <rect x="6" y="46" width="40" height="2.5" rx="0.5" fill="var(--accent)" opacity="0.8" />
        <rect x="6" y="52" width="78" height="1.5" rx="0.5" fill="#888" />
        <rect x="6" y="56" width="66" height="1.5" rx="0.5" fill="#888" />
        <rect x="6" y="60" width="78" height="1.5" rx="0.5" fill="#888" />

        {/* EI badge on doc */}
        <g transform="translate(75 20)">
          <rect x="-10" y="-4" width="18" height="8" rx="4" fill="#F5B800" />
          <text x="-1" y="1.5" textAnchor="middle" fontSize="5" fontWeight="800" fill="#4a3500">
            92%
          </text>
        </g>
      </g>

      {/* Sparkles around the finished doc */}
      <g className="sparkles">
        <g className="spark-1">
          <path d="M 270 195 L 272 199 L 276 201 L 272 203 L 270 207 L 268 203 L 264 201 L 268 199 Z" fill="var(--accent)" />
        </g>
        <g className="spark-2">
          <path d="M 360 230 L 362 234 L 366 236 L 362 238 L 360 242 L 358 238 L 354 236 L 358 234 Z" fill="#F5B800" />
        </g>
        <g className="spark-3">
          <path d="M 355 275 L 357 279 L 361 281 L 357 283 L 355 287 L 353 283 L 349 281 L 353 279 Z" fill="var(--accent)" />
        </g>
      </g>

      {/* Done label */}
      <g transform="translate(310 175)">
        <rect x="-30" y="-9" width="60" height="18" rx="9" fill="#22c55e" />
        <text x="0" y="4" textAnchor="middle" fontSize="9" fontWeight="800" fill="#fff">
          READY ✓
        </text>
      </g>
    </svg>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// All keyframes and trigger styles
// ──────────────────────────────────────────────────────────────────────────

function GlobalStyles() {
  return (
    <style jsx global>{`
      /* ─── Act card entry — inline styles handle opacity/transform ─ */

      /* ─── Connector ──────────────────────────────────────────────── */
      .connector-pulse {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: var(--accent);
        box-shadow: 0 0 10px var(--accent-glow);
        animation: connector-travel 1.8s ease-in-out infinite;
      }
      @keyframes connector-travel {
        0% {
          top: 0;
          opacity: 0;
        }
        20% {
          opacity: 1;
        }
        80% {
          opacity: 1;
        }
        100% {
          top: 100%;
          opacity: 0;
        }
      }

      /* ─── Bot blink (shared) ─────────────────────────────────────── */
      .bot-eyes-blink {
        animation: bot-blink 5s ease-in-out infinite;
        transform-origin: center;
      }
      @keyframes bot-blink {
        0%, 93%, 97%, 100% {
          transform: scaleY(1);
        }
        95% {
          transform: scaleY(0.1);
        }
      }

      /* ─── Scene 1: Transcribe ────────────────────────────────────── */
      .lecture-woosh {
        animation: lecture-woosh-move 4s ease-in-out infinite;
      }
      @keyframes lecture-woosh-move {
        0% { transform: translate(-45px, 0); opacity: 0; }
        15% { opacity: 1; }
        50% { transform: translate(35px, 0); opacity: 1; }
        65% { transform: translate(55px, 0); opacity: 0; }
        100% { transform: translate(55px, 0); opacity: 0; }
      }
      .soundwave-pulse > circle {
        transform-box: fill-box;
        transform-origin: center;
        animation: soundwave-grow 1.5s ease-out infinite;
      }
      .soundwave-pulse > circle:nth-child(1) { animation-delay: 0s; }
      .soundwave-pulse > circle:nth-child(2) { animation-delay: 0.3s; }
      .soundwave-pulse > circle:nth-child(3) { animation-delay: 0.6s; }
      @keyframes soundwave-grow {
        0% { transform: scale(0.3); opacity: 1; }
        100% { transform: scale(1.5); opacity: 0; }
      }
      .typing-arm-left {
        transform-box: fill-box;
        transform-origin: top center;
        animation: typing-tap 0.35s ease-in-out infinite;
      }
      .typing-arm-right {
        transform-box: fill-box;
        transform-origin: top center;
        animation: typing-tap 0.35s ease-in-out infinite 0.18s;
      }
      @keyframes typing-tap {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(3px); }
      }
      .typebar {
        transform-box: fill-box;
        transform-origin: center bottom;
        animation: typebar-strike 0.35s ease-in-out infinite;
      }
      @keyframes typebar-strike {
        0%, 100% { transform: translateY(0); opacity: 0.9; }
        50% { transform: translateY(6px); opacity: 1; }
      }
      .ding-sparkle {
        transform-box: fill-box;
        transform-origin: center;
        animation: ding-twinkle 1.4s ease-in-out infinite;
      }
      @keyframes ding-twinkle {
        0%, 60%, 100% { transform: scale(0); opacity: 0; }
        70% { transform: scale(1.4); opacity: 1; }
        85% { transform: scale(0.9); opacity: 0.8; }
      }
      .receipt-unroll {
        transform-box: fill-box;
        transform-origin: top center;
        animation: receipt-grow 4s ease-out infinite;
      }
      @keyframes receipt-grow {
        0% { transform: scaleY(0.3); opacity: 0.6; }
        80%, 100% { transform: scaleY(1); opacity: 1; }
      }
      .filmroll-unroll {
        transform-box: fill-box;
        transform-origin: top center;
        animation: receipt-grow 4s ease-out infinite 0.2s;
      }

      /* ─── Scene 2: Plan — bird's-eye stamp conveyor ──────────────
         Cycle: 18s (6s per paper × 3 papers). Inside each 6s window:
         0.0-0.5s: paper slides in from left
         0.5-1.8s: scan beam sweeps L→R across paper (quick scan)
         1.8-2.2s: arm's stamp tool presses down (impact at 2.2s)
         2.2-5.3s: score stays visible for 3+ seconds — the money shot
         5.3-6.0s: paper slides out to the right, next one queues up
         Papers are staggered with a --delay CSS variable that cascades
         to paper-cycle-bev, scan-beam and stamp-reveal so they stay in phase.
         The arm itself animates on a 6s loop (one stamp per paper). */
      .belt-scroll-bev {
        animation: belt-scroll-bev-move 1.6s linear infinite;
      }
      @keyframes belt-scroll-bev-move {
        0% { transform: translateX(0); }
        100% { transform: translateX(-40px); }
      }
      .paper-cycle-bev {
        animation: paper-cycle-bev-move 18s linear infinite;
        animation-delay: var(--delay, 0s);
      }
      @keyframes paper-cycle-bev-move {
        0% { transform: translateX(-260px); opacity: 0; }
        1.5% { opacity: 1; }
        3.9% { transform: translateX(0); opacity: 1; }
        22.2% { transform: translateX(0); opacity: 1; }
        23% { opacity: 1; }
        28% { transform: translateX(260px); opacity: 0; }
        28.1%, 100% { transform: translateX(260px); opacity: 0; }
      }
      /* Scan beam — SLOWER deliberate 1.5s sweep so you can see it scanning.
         Starts 0.3s after paper enters, finishes at 1.8s. */
      .scan-beam {
        animation: scan-beam-sweep 18s linear infinite;
        animation-delay: var(--delay, 0s);
      }
      @keyframes scan-beam-sweep {
        0%, 1.6% { transform: translateX(0); opacity: 0; }
        2% { transform: translateX(0); opacity: 0.9; }
        10% { transform: translateX(180px); opacity: 0.9; }
        10.5%, 100% { transform: translateX(180px); opacity: 0; }
      }
      /* Stamp appears at 11.1% (2.0s) right after scan finishes.
         Stays until 22.2% (4.0s) — 2 seconds visible, snappy — then paper
         exits and next paper queues up quickly. */
      .stamp-reveal {
        transform-box: fill-box;
        animation: stamp-reveal-pop 18s ease-out infinite;
        animation-delay: var(--delay, 0s);
      }
      @keyframes stamp-reveal-pop {
        0%, 11% { opacity: 0; transform: scale(0); }
        11.1% { opacity: 1; transform: scale(1.35); }
        12% { transform: scale(0.95); }
        13% { transform: scale(1); }
        22.2% { opacity: 1; transform: scale(1); }
        23% { opacity: 0; transform: scale(1); }
        100% { opacity: 0; transform: scale(1); }
      }
      /* Arm extends during scan (0.3-1.8s), presses at 2.0s, retracts
         immediately after so score is visible unobstructed. */
      .arm-extend-retract {
        animation: arm-extend-retract-move 6s ease-in-out infinite;
      }
      @keyframes arm-extend-retract-move {
        0%, 3% { transform: translateX(90px); }
        8% { transform: translateX(0); }
        33% { transform: translateX(0); }
        38% { transform: translateX(90px); }
        100% { transform: translateX(90px); }
      }
      /* Stamp tool — visible scan hover, then presses at ~2.0s (33% of 6s). */
      .arm-stamp-tool {
        transform-box: fill-box;
        transform-origin: 285px 137px;
        animation: arm-stamp-action 6s ease-in-out infinite;
      }
      @keyframes arm-stamp-action {
        0%, 10% { transform: translate(0, 0); }
        15% { transform: translate(1px, 0); }
        22% { transform: translate(-1px, 0); }
        30% { transform: translate(0, 0); }
        33% { transform: translate(0, 10px); }
        37% { transform: translate(0, 0); }
        100% { transform: translate(0, 0); }
      }
      .stamp-impact-ring {
        transform-box: fill-box;
        transform-origin: 285px 142px;
        opacity: 0;
        animation: stamp-impact-ring-pulse 6s ease-out infinite;
      }
      @keyframes stamp-impact-ring-pulse {
        0%, 31% { opacity: 0; transform: scale(0.4); }
        33% { opacity: 0.9; transform: scale(0.9); }
        40% { opacity: 0; transform: scale(1.6); }
        41%, 100% { opacity: 0; transform: scale(1.6); }
      }

      /* ─── Scene 3: Gym pushups — two-pose flipbook ─────────────────
         Real pushup: arms STRAIGHT at top, BENT at bottom (elbows flared
         back, body close to ground). We flipbook between two drawn poses
         so the arm bending is visible, not just a body bounce.
         Cycle: 1.2s per rep. Hold at top (strong phase), quick drop,
         brief pause at bottom (peak effort), quick push back up. */
      .pushup-up {
        opacity: 1;
        animation: pushup-up-fade 1.2s ease-in-out infinite;
      }
      .pushup-down {
        opacity: 0;
        animation: pushup-down-fade 1.2s ease-in-out infinite;
      }
      @keyframes pushup-up-fade {
        0%, 35% { opacity: 1; }
        42%, 85% { opacity: 0; }
        92%, 100% { opacity: 1; }
      }
      @keyframes pushup-down-fade {
        0%, 35% { opacity: 0; }
        42%, 85% { opacity: 1; }
        92%, 100% { opacity: 0; }
      }
      .sweat-drop {
        transform-box: fill-box;
        transform-origin: center;
        opacity: 0;
      }
      .sweat-1 { animation: sweat-fly 2.2s ease-in infinite; }
      .sweat-2 { animation: sweat-fly 2.2s ease-in infinite 1.1s; }
      @keyframes sweat-fly {
        0% { transform: translate(0, 0) scale(1); opacity: 0; }
        15% { opacity: 1; }
        100% { transform: translate(6px, 30px) scale(0.6); opacity: 0; }
      }
      .effort-lines {
        animation: effort-blink 0.95s ease-in-out infinite;
      }
      @keyframes effort-blink {
        0%, 100% { opacity: 0.2; }
        50% { opacity: 0.9; }
      }
      .clock-min {
        transform-box: fill-box;
        transform-origin: 0 12.5px;
        animation: clock-min-tick 6s linear infinite;
      }
      @keyframes clock-min-tick {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }

      /* ─── Scene 4: Fact-check ────────────────────────────────────── */
      .magnifier-sweep {
        animation: magnifier-move 4s ease-in-out infinite;
      }
      @keyframes magnifier-move {
        0% {
          transform: translate(80px, 80px);
        }
        25% {
          transform: translate(170px, 80px);
        }
        50% {
          transform: translate(170px, 140px);
        }
        75% {
          transform: translate(80px, 180px);
        }
        100% {
          transform: translate(80px, 80px);
        }
      }
      .check-stamp {
        transform-origin: center;
        opacity: 0;
      }
      .check-1 {
        animation: check-pop 4s ease-out infinite 0.5s;
      }
      .check-2 {
        animation: check-pop 4s ease-out infinite 1.5s;
      }
      .check-3 {
        animation: check-pop 4s ease-out infinite 2.5s;
      }
      @keyframes check-pop {
        0%, 20% {
          opacity: 0;
          transform: scale(0.2);
        }
        25% {
          opacity: 1;
          transform: scale(1.25);
        }
        30% {
          transform: scale(1);
        }
        85% {
          opacity: 1;
          transform: scale(1);
        }
        100% {
          opacity: 1;
          transform: scale(1);
        }
      }
      .textbook-float {
        animation: textbook-float-move 3.5s ease-in-out infinite;
      }
      @keyframes textbook-float-move {
        0%, 100% {
          transform: translate(275px, 50px) rotate(-2deg);
        }
        50% {
          transform: translate(275px, 44px) rotate(2deg);
        }
      }
      .reference-beam {
        stroke-dasharray: 3 3;
        animation: beam-flow 1.2s linear infinite;
      }
      @keyframes beam-flow {
        0% {
          stroke-dashoffset: 0;
        }
        100% {
          stroke-dashoffset: -12;
        }
      }

      /* ─── Scene 5: Output ────────────────────────────────────────── */
      .smoke-puffs circle {
        transform-origin: center;
      }
      .smoke-1 {
        animation: smoke-rise 2.4s ease-out infinite;
      }
      .smoke-2 {
        animation: smoke-rise 2.4s ease-out infinite 0.8s;
      }
      .smoke-3 {
        animation: smoke-rise 2.4s ease-out infinite 1.6s;
      }
      @keyframes smoke-rise {
        0% {
          transform: translateY(15px) scale(0.6);
          opacity: 0;
        }
        30% {
          opacity: 0.4;
        }
        100% {
          transform: translateY(-30px) scale(1.4);
          opacity: 0;
        }
      }
      .window-flicker-1 {
        animation: window-flicker 2.5s ease-in-out infinite;
      }
      .window-flicker-2 {
        animation: window-flicker 2.5s ease-in-out infinite 0.4s;
      }
      .window-flicker-3 {
        animation: window-flicker 2.5s ease-in-out infinite 0.8s;
      }
      @keyframes window-flicker {
        0%, 100% {
          opacity: 0.9;
        }
        50% {
          opacity: 0.55;
        }
      }
      .output-doc {
        animation: doc-emerge 4s ease-out infinite;
      }
      @keyframes doc-emerge {
        0% {
          transform: translate(220px, 215px) scale(0.85);
          opacity: 0;
        }
        20% {
          opacity: 1;
        }
        45% {
          transform: translate(265px, 200px) scale(1);
          opacity: 1;
        }
        95%, 100% {
          transform: translate(265px, 200px) scale(1);
          opacity: 1;
        }
      }
      .sparkles g {
        transform-origin: center;
        transform-box: fill-box;
      }
      .spark-1 {
        animation: spark-twinkle 2s ease-in-out infinite 0.2s;
      }
      .spark-2 {
        animation: spark-twinkle 2s ease-in-out infinite 0.8s;
      }
      .spark-3 {
        animation: spark-twinkle 2s ease-in-out infinite 1.4s;
      }
      @keyframes spark-twinkle {
        0%, 100% {
          opacity: 0;
          transform: scale(0.3);
        }
        50% {
          opacity: 1;
          transform: scale(1);
        }
      }

      /* ─── Reduced motion ─────────────────────────────────────────── */
      @media (prefers-reduced-motion: reduce) {
        .lecture-woosh,
        .soundwave-pulse > circle,
        .typing-arm-left,
        .typing-arm-right,
        .typebar,
        .ding-sparkle,
        .receipt-unroll,
        .belt-scroll-bev,
        .paper-cycle-bev,
        .scan-beam,
        .stamp-reveal,
        .arm-extend-retract,
        .arm-stamp-tool,
        .stamp-impact-ring,
        .pushup-up,
        .pushup-down,
        .sweat-drop,
        .effort-lines,
        .clock-min,
        .magnifier-sweep,
        .check-stamp,
        .textbook-float,
        .reference-beam,
        .smoke-puffs circle,
        .output-doc,
        .sparkles g,
        .window-flicker-1,
        .window-flicker-2,
        .window-flicker-3,
        .connector-pulse,
        .bot-eyes-blink {
          animation: none !important;
        }
        .check-stamp,
        .output-doc,
        .sparkles g,
        .stamp-reveal,
        .sweat-drop {
          opacity: 1 !important;
        }
      }
    `}</style>
  );
}
