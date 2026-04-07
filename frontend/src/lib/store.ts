import { create } from "zustand";
import { ConceptGroup, VerificationClaim, TrustStats } from "./types";
import { computeTrustStats } from "./data";

export interface PipelineStage {
  name: string;
  weight: number;
  mockDuration: number;
  mockResult: string;
  hasSubProgress?: boolean;
  subTotal?: number;
  status: "pending" | "running" | "done";
  result?: string;
}

export interface AppSettings {
  model: string;
  skipCI: boolean;
  skipVerify: boolean;
  skipCompleteness: boolean;
  skipSlides: boolean;
  llmGrouping: boolean;
  dryRun: boolean;
}

export interface UserState {
  isLoggedIn: boolean;
  name: string;
  email: string;
  avatar: string | null;
}

export interface Session {
  id: string;
  name: string;
  date: string;
  groups: number;
}

interface AppState {
  // User
  user: UserState;
  signIn: (name: string, email: string) => void;
  signOut: () => void;

  // Sessions
  sessions: Session[];

  // Sidebar
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;

  // Upload
  transcriptFile: File | null;
  videoFile: File | null;
  setTranscriptFile: (f: File | null) => void;
  setVideoFile: (f: File | null) => void;

  // Pipeline
  stages: PipelineStage[];
  currentStageIndex: number;
  subProgress: number;
  isProcessing: boolean;
  isDone: boolean;
  startPipeline: () => void;
  cancelPipeline: () => void;

  // Output
  markdown: string;
  groups: ConceptGroup[];
  trustStats: TrustStats;
  setOutput: (md: string, groups: ConceptGroup[], claims: VerificationClaim[]) => void;

  // Settings
  settings: AppSettings;
  updateSettings: (partial: Partial<AppSettings>) => void;

  // Reset
  reset: () => void;
}

const MOCK_SESSIONS: Session[] = [
  { id: "1", name: "Virology Lecture 3", date: "Apr 7, 2026", groups: 8 },
  { id: "2", name: "Immunology Lecture 5", date: "Apr 5, 2026", groups: 6 },
  { id: "3", name: "Anatomy Lecture 12", date: "Apr 3, 2026", groups: 10 },
];

const DEFAULT_STAGES: PipelineStage[] = [
  { name: "Chunking transcript", weight: 5, mockDuration: 800, mockResult: "14 chunks, 3 need expansion", status: "pending" },
  { name: "Scoring exam importance", weight: 5, mockDuration: 600, mockResult: "CI% range: 8–95%", status: "pending" },
  { name: "Transcribing lecture", weight: 5, mockDuration: 700, mockResult: "15,017 words transcribed", status: "pending" },
  { name: "Grouping concepts", weight: 5, mockDuration: 500, mockResult: "8 groups (1 skipped, 1 minimal)", status: "pending" },
  { name: "Generating explanations", weight: 60, mockDuration: 3000, mockResult: "7 sections generated", hasSubProgress: true, subTotal: 8, status: "pending" },
  { name: "Verifying sources", weight: 8, mockDuration: 600, mockResult: "Sources verified against textbooks", status: "pending" },
  { name: "Checking completeness", weight: 5, mockDuration: 400, mockResult: "97% key terms covered", status: "pending" },
  { name: "Inserting slide references", weight: 4, mockDuration: 300, mockResult: "12 slides mapped", status: "pending" },
  { name: "Assembling final document", weight: 3, mockDuration: 200, mockResult: "Done!", status: "pending" },
];

const DEFAULT_SETTINGS: AppSettings = {
  model: "gemini-3.1-pro",
  skipCI: false,
  skipVerify: false,
  skipCompleteness: false,
  skipSlides: false,
  llmGrouping: false,
  dryRun: false,
};

let pipelineTimer: ReturnType<typeof setTimeout> | null = null;
let subProgressTimer: ReturnType<typeof setInterval> | null = null;

export const useAppStore = create<AppState>((set, get) => ({
  // User
  user: { isLoggedIn: false, name: "Guest", email: "", avatar: null },
  signIn: (name, email) =>
    set({ user: { isLoggedIn: true, name, email, avatar: null } }),
  signOut: () =>
    set({ user: { isLoggedIn: false, name: "Guest", email: "", avatar: null } }),

  // Sessions
  sessions: MOCK_SESSIONS,

  // Sidebar
  sidebarOpen: true,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),

  // Upload
  transcriptFile: null,
  videoFile: null,
  setTranscriptFile: (f) => set({ transcriptFile: f }),
  setVideoFile: (f) => set({ videoFile: f }),

  // Pipeline
  stages: DEFAULT_STAGES.map((s) => ({ ...s })),
  currentStageIndex: -1,
  subProgress: 0,
  isProcessing: false,
  isDone: false,

  startPipeline: () => {
    const stages = DEFAULT_STAGES.map((s) => ({ ...s, status: "pending" as const }));
    set({ stages, currentStageIndex: 0, subProgress: 0, isProcessing: true, isDone: false });

    const runStage = (index: number) => {
      if (index >= stages.length) {
        // All done — load output
        set({ isProcessing: false, isDone: true });
        // Load existing v4 files as "output"
        Promise.all([
          fetch("/data/v4_lecture_replacement.md").then((r) => r.text()),
          fetch("/data/v4_concept_groups.json").then((r) => r.json()),
          fetch("/data/v4_verification_report.json").then((r) => r.json()),
        ]).then(([md, groups, claims]) => {
          get().setOutput(md, groups, claims);
        });
        return;
      }

      // Mark current stage as running
      set((state) => {
        const newStages = [...state.stages];
        newStages[index] = { ...newStages[index], status: "running" };
        return { stages: newStages, currentStageIndex: index, subProgress: 0 };
      });

      // Simulate sub-progress for generation stage
      if (stages[index].hasSubProgress) {
        const subTotal = stages[index].subTotal || 8;
        const interval = stages[index].mockDuration / subTotal;
        let sub = 0;
        subProgressTimer = setInterval(() => {
          sub++;
          set({ subProgress: sub });
          if (sub >= subTotal && subProgressTimer) {
            clearInterval(subProgressTimer);
            subProgressTimer = null;
          }
        }, interval);
      }

      // Complete stage after mock duration
      pipelineTimer = setTimeout(() => {
        if (subProgressTimer) {
          clearInterval(subProgressTimer);
          subProgressTimer = null;
        }

        set((state) => {
          const newStages = [...state.stages];
          newStages[index] = {
            ...newStages[index],
            status: "done",
            result: newStages[index].mockResult,
          };
          return { stages: newStages };
        });

        // Run next stage
        runStage(index + 1);
      }, stages[index].mockDuration);
    };

    runStage(0);
  },

  cancelPipeline: () => {
    if (pipelineTimer) clearTimeout(pipelineTimer);
    if (subProgressTimer) clearInterval(subProgressTimer);
    pipelineTimer = null;
    subProgressTimer = null;
    set({
      isProcessing: false,
      isDone: false,
      currentStageIndex: -1,
      stages: DEFAULT_STAGES.map((s) => ({ ...s })),
    });
  },

  // Output
  markdown: "",
  groups: [],
  trustStats: { totalClaims: 0, correctClaims: 0, verifiedPercent: 0 },
  setOutput: (md, groups, claims) =>
    set({
      markdown: md,
      groups,
      trustStats: computeTrustStats(claims),
    }),

  // Settings
  settings: { ...DEFAULT_SETTINGS },
  updateSettings: (partial) =>
    set((state) => ({ settings: { ...state.settings, ...partial } })),

  // Reset
  reset: () => {
    if (pipelineTimer) clearTimeout(pipelineTimer);
    if (subProgressTimer) clearInterval(subProgressTimer);
    set({
      transcriptFile: null,
      videoFile: null,
      stages: DEFAULT_STAGES.map((s) => ({ ...s })),
      currentStageIndex: -1,
      subProgress: 0,
      isProcessing: false,
      isDone: false,
      markdown: "",
      groups: [],
      trustStats: { totalClaims: 0, correctClaims: 0, verifiedPercent: 0 },
    });
  },
}));
