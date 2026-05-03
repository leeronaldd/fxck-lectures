"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Browser-native TTS button. Uses Web Speech API (free, instant, no backend
 * call) to read a section's narrative aloud. Picks the most "Klare-like"
 * voice available on the user's OS — Microsoft Emma if present (matches the
 * pipeline's edge-tts voice exactly), falling back to other warm female
 * English voices.
 *
 * The reader integration is per-section: every NarrativeSection renders one
 * of these next to its title, so a student can hit "Read aloud" on any
 * concept and Klare reads that section out loud while they follow along.
 *
 * Future v2: stream audio from a backend endpoint that calls the same
 * edge-tts pipeline we use for the video generation — guarantees identical
 * voice across browsers/OSes. For now, browser-native is good enough.
 */
export default function ReadAloudButton({ text }: { text: string }) {
  const [playing, setPlaying] = useState(false);
  const [voice, setVoice] = useState<SpeechSynthesisVoice | null>(null);
  const [supported, setSupported] = useState(true);
  const utterRef = useRef<SpeechSynthesisUtterance | null>(null);

  // Pick best available voice. getVoices() can return [] until the browser
  // loads its voice list — listen for voiceschanged for the second pass.
  useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      setSupported(false);
      return;
    }
    function pick() {
      const all = window.speechSynthesis.getVoices();
      if (all.length === 0) return;
      // Preference order: closest to our pipeline's en-US-EmmaMultilingualNeural
      const preferences = [
        /Emma.*Natural/i,
        /^Microsoft Emma/i,
        /Aria.*Natural/i,
        /^Microsoft Aria/i,
        /^Samantha$/,
        /Google US English/i,
        /female/i,
      ];
      let best: SpeechSynthesisVoice | undefined;
      for (const re of preferences) {
        best = all.find(v => re.test(v.name) && /^en/i.test(v.lang));
        if (best) break;
      }
      if (!best) {
        best = all.find(v => /^en-?US/i.test(v.lang))
            || all.find(v => /^en/i.test(v.lang))
            || all[0];
      }
      setVoice(best || null);
    }
    pick();
    window.speechSynthesis.addEventListener("voiceschanged", pick);
    return () => window.speechSynthesis.removeEventListener("voiceschanged", pick);
  }, []);

  // Cancel speech if the component unmounts mid-read (route change, etc.)
  useEffect(() => () => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  }, []);

  function toggle() {
    if (!supported) return;
    if (playing) {
      window.speechSynthesis.cancel();
      setPlaying(false);
      utterRef.current = null;
      return;
    }
    // Cancel any utterance from a different section that's still playing
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    if (voice) utter.voice = voice;
    utter.rate = 1.05;
    utter.pitch = 1.0;
    utter.onstart = () => setPlaying(true);
    utter.onend = () => { setPlaying(false); utterRef.current = null; };
    utter.onerror = () => { setPlaying(false); utterRef.current = null; };
    utterRef.current = utter;
    window.speechSynthesis.speak(utter);
    // Some browsers don't fire onstart reliably — flip immediately
    setPlaying(true);
  }

  if (!supported) return null;

  return (
    <button
      type="button"
      onClick={toggle}
      title={playing ? "Stop reading" : "Read this section aloud"}
      className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all shrink-0"
      style={{
        background: playing ? "var(--accent)" : "var(--bg-elevated)",
        color: playing ? "#fff" : "var(--text-secondary)",
        border: `1px solid ${playing ? "var(--accent)" : "var(--border)"}`,
        boxShadow: playing ? "0 0 20px rgba(255, 107, 53, 0.4)" : "none",
      }}
      onMouseEnter={(e) => {
        if (!playing) {
          e.currentTarget.style.color = "var(--accent)";
          e.currentTarget.style.borderColor = "var(--accent)";
        }
      }}
      onMouseLeave={(e) => {
        if (!playing) {
          e.currentTarget.style.color = "var(--text-secondary)";
          e.currentTarget.style.borderColor = "var(--border)";
        }
      }}
      aria-label={playing ? "Stop reading aloud" : "Read aloud"}
      aria-pressed={playing}
    >
      {playing ? (
        <>
          {/* Animated 4-bar waveform — visual cue that audio is playing */}
          <span className="inline-flex items-end gap-[2px] h-3" aria-hidden>
            <span className="tts-wave-bar" style={{ height: "60%", animationDelay: "0s" }} />
            <span className="tts-wave-bar" style={{ height: "100%", animationDelay: "0.15s" }} />
            <span className="tts-wave-bar" style={{ height: "70%", animationDelay: "0.3s" }} />
            <span className="tts-wave-bar" style={{ height: "90%", animationDelay: "0.45s" }} />
          </span>
          Reading
        </>
      ) : (
        <>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/>
          </svg>
          Read aloud
        </>
      )}
    </button>
  );
}
