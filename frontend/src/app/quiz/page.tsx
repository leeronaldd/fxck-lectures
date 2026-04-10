"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";

interface QuizAnswer {
  question: string;
  answer: string;
}

const QUESTIONS = [
  {
    id: 1,
    question: "What are you studying?",
    subtitle: "This helps us match the right depth for your course.",
    options: [
      "Medicine / Biomedical Science",
      "Nursing / Midwifery",
      "Pharmacy",
      "Dentistry",
      "Other health science",
    ],
  },
  {
    id: 2,
    question: "What year are you in?",
    subtitle: "We'll adjust how much we assume you already know.",
    options: ["1st year", "2nd year", "3rd year", "4th year+"],
  },
  {
    id: 3,
    question: "What frustrates you most about lectures?",
    subtitle: "Pick the one that hits hardest.",
    options: [
      "Spend more time decoding the professor than actually learning",
      "Too much content",
      "Professor yaps on easy stuff and skims the hard stuff",
      "I don't know what's getting tested",
    ],
  },
  {
    id: 4,
    question: "How did you hear about us?",
    subtitle: "Last one \u2014 helps us know what's working.",
    options: [
      "Friend / classmate",
      "TikTok / Instagram",
      "Google search",
      "Other",
    ],
  },
];

export default function QuizPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<QuizAnswer[]>([]);
  const [fadingOut, setFadingOut] = useState(false);

  const totalSteps = QUESTIONS.length;
  const progressPercent = Math.round(((step + 1) / totalSteps) * 100);

  const transition = useCallback((next: () => void) => {
    setFadingOut(true);
    setTimeout(() => {
      next();
      setFadingOut(false);
    }, 250);
  }, []);

  function selectAnswer(answer: string) {
    const q = QUESTIONS[step];
    setAnswers((prev) => {
      const filtered = prev.filter((a) => a.question !== q.question);
      return [...filtered, { question: q.question, answer }];
    });

    setTimeout(() => {
      if (step < QUESTIONS.length - 1) {
        transition(() => setStep(step + 1));
      } else {
        // Quiz complete — save to localStorage and go to sign-in
        const finalAnswers = [
          ...answers.filter((a) => a.question !== q.question),
          { question: q.question, answer },
        ];
        localStorage.setItem("klare_quiz", JSON.stringify(finalAnswers));
        router.push("/signin");
      }
    }, 300);
  }

  function goBack() {
    if (step > 0) {
      transition(() => setStep(step - 1));
    }
  }

  const currentQ = QUESTIONS[step];
  const currentAnswer = answers.find((a) => a.question === currentQ.question)?.answer;

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--bg-base, #0a0a0f)" }}
    >
      {/* Progress bar */}
      <div className="w-full px-4 pt-6 pb-2">
        <div className="max-w-lg mx-auto flex items-center gap-3">
          {step > 0 && (
            <button
              onClick={goBack}
              className="p-1 rounded-lg transition-colors"
              style={{ color: "var(--text-muted)" }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </button>
          )}
          <div className="flex-1 h-1.5 rounded-full" style={{ background: "var(--bg-elevated, #1a1a2e)" }}>
            <div
              className="h-full rounded-full transition-all duration-500 ease-out"
              style={{
                width: `${progressPercent}%`,
                background: "linear-gradient(90deg, #FF6B35, #FF8555)",
              }}
            />
          </div>
          <span className="text-xs tabular-nums" style={{ color: "var(--text-muted)" }}>
            {step + 1}/{totalSteps}
          </span>
        </div>
      </div>

      {/* Question */}
      <div className="flex-1 flex items-center justify-center px-4 py-8">
        <div
          className={`w-full max-w-lg transition-all duration-250 ${
            fadingOut ? "opacity-0 translate-y-2" : "opacity-100 translate-y-0"
          }`}
        >
          <h1
            className="text-2xl font-bold mb-2 text-center"
            style={{ color: "var(--text-primary, #fff)" }}
          >
            {currentQ.question}
          </h1>
          <p
            className="text-sm mb-8 text-center"
            style={{ color: "var(--text-muted, #888)" }}
          >
            {currentQ.subtitle}
          </p>

          {/* Options */}
          <div className="space-y-3">
            {currentQ.options.map((option) => {
              const isSelected = currentAnswer === option;
              return (
                <button
                  key={option}
                  onClick={() => selectAnswer(option)}
                  className="w-full text-left px-5 py-4 rounded-xl text-sm font-medium transition-all"
                  style={{
                    background: isSelected
                      ? "rgba(255, 107, 53, 0.15)"
                      : "var(--bg-elevated, #1a1a2e)",
                    border: isSelected
                      ? "1px solid rgba(255, 107, 53, 0.4)"
                      : "1px solid var(--border, #2a2a3e)",
                    color: isSelected
                      ? "#FF6B35"
                      : "var(--text-primary, #fff)",
                  }}
                >
                  {option}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Klare branding */}
      <div className="pb-6 text-center">
        <span className="text-xs" style={{ color: "var(--text-muted, #555)" }}>
          Klare
        </span>
      </div>
    </div>
  );
}
