import { create } from "zustand";
import { toast } from "sonner";
import { ConceptGroup, VerificationClaim, TrustStats } from "./types";
import { computeTrustStats } from "./data";
import { uploadFile, runPipeline, fetchSessions, fetchSession } from "./api";
import type { PipelineEvent } from "./api";

export interface PipelineStage {
  name: string;
  weight: number;
  mockDuration: number;
  mockResult: string;
  hasSubProgress?: boolean;
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
  loadSessions: () => void;
  loadSession: (sessionId: string) => Promise<void>;

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
  uploadProgress: number; // 0-100 upload percentage
  isUploading: boolean;
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

// Sessions will be loaded from Supabase DB in the future
const INITIAL_SESSIONS: Session[] = [];

const TEXT_STAGES: PipelineStage[] = [
  { name: "Chunking transcript", weight: 5, mockDuration: 800, mockResult: "14 chunks", status: "pending" },
  { name: "Scoring exam importance", weight: 5, mockDuration: 600, mockResult: "CI% scored", status: "pending" },
  { name: "Grouping concepts", weight: 5, mockDuration: 500, mockResult: "8 groups", status: "pending" },
  { name: "Generating explanations", weight: 60, mockDuration: 3000, mockResult: "7 sections generated", hasSubProgress: true, status: "pending" },
  { name: "Verifying sources", weight: 8, mockDuration: 600, mockResult: "Sources verified", status: "pending" },
  { name: "Checking completeness", weight: 5, mockDuration: 400, mockResult: "97% covered", status: "pending" },
  { name: "Inserting slide references", weight: 4, mockDuration: 300, mockResult: "12 slides mapped", status: "pending" },
  { name: "Assembling final document", weight: 3, mockDuration: 200, mockResult: "Done!", status: "pending" },
];

const VIDEO_STAGES: PipelineStage[] = [
  { name: "Transcribing lecture", weight: 15, mockDuration: 2000, mockResult: "Transcribed", status: "pending" },
  { name: "Chunking transcript", weight: 5, mockDuration: 800, mockResult: "14 chunks", status: "pending" },
  { name: "Scoring exam importance", weight: 5, mockDuration: 600, mockResult: "CI% scored", status: "pending" },
  { name: "Grouping concepts", weight: 5, mockDuration: 500, mockResult: "8 groups", status: "pending" },
  { name: "Generating explanations", weight: 50, mockDuration: 3000, mockResult: "7 sections generated", hasSubProgress: true, status: "pending" },
  { name: "Verifying sources", weight: 8, mockDuration: 600, mockResult: "Sources verified", status: "pending" },
  { name: "Checking completeness", weight: 5, mockDuration: 400, mockResult: "97% covered", status: "pending" },
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
  sessions: INITIAL_SESSIONS,
  loadSessions: () => {
    fetchSessions().then((data) => {
      const sessions: Session[] = data.map((s) => ({
        id: s.id,
        name: s.name,
        date: new Date(s.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
        groups: 0,
      }));
      set({ sessions });
    }).catch(() => {});
  },
  loadSession: async (sessionId: string) => {
    const data = await fetchSession(sessionId);
    if (data) {
      get().setOutput(
        data.markdown,
        (data.concept_groups || []) as ConceptGroup[],
        (data.verification_report || []) as VerificationClaim[],
      );
    }
  },

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
  stages: TEXT_STAGES.map((s) => ({ ...s })),
  currentStageIndex: -1,
  subProgress: 0,
  isProcessing: false,
  isDone: false,
  pipelineError: null,

  uploadProgress: 0,
  isUploading: false,

  startPipeline: () => {
    const file = get().transcriptFile || get().videoFile;
    if (!file) {
      set({ isProcessing: false, isUploading: false, pipelineError: "No file selected" });
      toast.error("No file selected");
      return;
    }

    const isVideo = /\.(mp4|mkv|avi|mov|webm)$/i.test(file.name);
    const stageTemplate = isVideo ? VIDEO_STAGES : TEXT_STAGES;
    const stages = stageTemplate.map((s) => ({ ...s, status: "pending" as const }));

    // Build stageMap dynamically from chosen stages
    const stageMap: Record<string, number> = {};
    stages.forEach((s, i) => { stageMap[s.name] = i; });
    stageMap["Done"] = stages.length - 1;

    set({ stages, currentStageIndex: -1, subProgress: 0, isProcessing: true, isDone: false, pipelineError: null, uploadProgress: 0, isUploading: true });

    // Upload file with progress, then stream pipeline via SSE
    (async () => {
      try {
        toast.loading("Uploading lecture...", { id: "upload" });

        const { file_id } = await uploadFile(file, (percent) => {
          set({ uploadProgress: percent });
        });

        set({ isUploading: false, uploadProgress: 100, currentStageIndex: 0 });
        toast.success("Upload complete!", { id: "upload" });
        toast.loading("Processing lecture...", { id: "pipeline" });

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
            toast.error(`Pipeline failed: ${error}`, { id: "pipeline" });
          },
          // onDone
          (output) => {
            cancelStream = null;
            set((state) => {
              const newStages = state.stages.map((s) => ({ ...s, status: "done" as const }));
              return { stages: newStages, isProcessing: false, isDone: true };
            });
            toast.success("Your lecture is ready!", { id: "pipeline", duration: 5000 });

            if (output) {
              get().setOutput(
                output.markdown,
                (output.concept_groups || []) as ConceptGroup[],
                (output.verification_report || []) as VerificationClaim[],
              );
            }
            // Refresh sessions list
            get().loadSessions();
          },
        );
      } catch (err) {
        console.error("[Pipeline] Error:", err);
        const message = err instanceof Error ? err.message : "Upload failed";
        set({ isProcessing: false, isUploading: false, pipelineError: message });
        toast.error(message, { id: "upload" });
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
      stages: TEXT_STAGES.map((s) => ({ ...s })),
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
      stages: TEXT_STAGES.map((s) => ({ ...s })),
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
