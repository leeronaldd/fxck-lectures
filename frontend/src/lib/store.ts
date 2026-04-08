import { create } from "zustand";
import { ConceptGroup, VerificationClaim, TrustStats } from "./types";
import { computeTrustStats } from "./data";
import { uploadFile, runPipeline } from "./api";
import type { PipelineEvent } from "./api";

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
  id: string;
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
  authLoading: boolean;
  setUser: (user: UserState) => void;
  clearUser: () => void;
  setAuthLoading: (loading: boolean) => void;

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
  pipelineError: string | null;
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

let cancelStream: (() => void) | null = null;

export const useAppStore = create<AppState>((set, get) => {
  // Expose store for debugging (remove in production)
  if (typeof window !== "undefined") {
    (window as unknown as Record<string, unknown>).__store = { getState: () => get(), setState: set };
  }
  return ({
  // User
  user: { isLoggedIn: false, id: "", name: "Guest", email: "", avatar: null },
  authLoading: true,
  setUser: (user) => set({ user }),
  clearUser: () =>
    set({ user: { isLoggedIn: false, id: "", name: "Guest", email: "", avatar: null } }),
  setAuthLoading: (loading) => set({ authLoading: loading }),

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
  pipelineError: null,

  startPipeline: () => {
    const stages = DEFAULT_STAGES.map((s) => ({ ...s, status: "pending" as const }));
    set({ stages, currentStageIndex: 0, subProgress: 0, isProcessing: true, isDone: false, pipelineError: null });

    const file = get().transcriptFile || get().videoFile;
    if (!file) {
      set({ isProcessing: false, pipelineError: "No file selected" });
      return;
    }

    const stageMap: Record<string, number> = {
      "Chunking transcript": 0,
      "Scoring exam importance": 1,
      "Transcribing lecture": 2,
      "Grouping concepts": 3,
      "Generating explanations": 4,
      "Verifying sources": 5,
      "Checking completeness": 6,
      "Inserting slide references": 7,
      "Assembling final document": 8,
      "Done": 8,
    };

    // Upload file, then stream pipeline via SSE
    (async () => {
      try {
        set((state) => {
          const s = [...state.stages];
          s[0] = { ...s[0], status: "running" };
          return { stages: s, currentStageIndex: 0 };
        });

        const { file_id } = await uploadFile(file);

        // Run pipeline via SSE — connection stays alive the entire time
        cancelStream = runPipeline(
          file_id,
          // onUpdate
          (event: PipelineEvent) => {
            const stageIndex = event.current_stage ? (stageMap[event.current_stage] ?? -1) : -1;
            set((state) => {
              const newStages = [...state.stages];
              for (let i = 0; i < newStages.length; i++) {
                if (i < stageIndex) {
                  newStages[i] = { ...newStages[i], status: "done" };
                } else if (i === stageIndex) {
                  newStages[i] = { ...newStages[i], status: "running" };
                }
              }
              return { stages: newStages, currentStageIndex: stageIndex, subProgress: event.progress };
            });
          },
          // onError
          (error) => {
            cancelStream = null;
            set({ isProcessing: false, pipelineError: error });
          },
          // onDone
          (output) => {
            cancelStream = null;
            set((state) => {
              const newStages = state.stages.map((s) => ({ ...s, status: "done" as const }));
              return { stages: newStages, isProcessing: false, isDone: true };
            });

            if (output) {
              get().setOutput(
                output.markdown,
                (output.concept_groups || []) as ConceptGroup[],
                (output.verification_report || []) as VerificationClaim[],
              );
            }
          },
        );
      } catch (err) {
        console.error("[Pipeline] Error:", err);
        set({ isProcessing: false, pipelineError: err instanceof Error ? err.message : "Upload failed" });
      }
    })();
  },

  cancelPipeline: () => {
    if (cancelStream) cancelStream();
    cancelStream = null;
    set({
      isProcessing: false,
      isDone: false,
      pipelineError: null,
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
    if (cancelStream) cancelStream();
    cancelStream = null;
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
})});
