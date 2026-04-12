import { create } from "zustand";
import { toast } from "sonner";
import { ConceptGroup, VerificationClaim, TrustStats } from "./types";
import { computeTrustStats } from "./data";
import { uploadFile, uploadSlides, runPipeline, fetchSessions, fetchSession, createSession as apiCreateSession } from "./api";
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

// Per-session pipeline state for concurrent processing
export interface PipelineRun {
  sessionName: string;
  fileId: string;
  stages: PipelineStage[];
  currentStageIndex: number;
  subProgress: number;
  isProcessing: boolean;
  isDone: boolean;
  error: string | null;
  isUploading: boolean;
  uploadProgress: number;
  cancel: (() => void) | null;
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
  activeSessionId: string | null;
  loadSessions: () => Promise<void>;
  loadSession: (sessionId: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  createNewSession: () => Promise<string | null>;

  // Sidebar
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;

  // Upload
  transcriptFile: File | null;
  videoFile: File | null;
  slidesFile: File | null;
  setTranscriptFile: (f: File | null) => void;
  setVideoFile: (f: File | null) => void;
  setSlidesFile: (f: File | null) => void;

  // Pipeline — per-session concurrent runs
  pipelineRuns: Record<string, PipelineRun>;  // keyed by fileId
  activePipelineId: string | null;            // which run is currently viewed
  startPipeline: () => void;
  cancelPipeline: (fileId?: string) => void;

  // Legacy accessors — read from active pipeline run
  stages: PipelineStage[];
  currentStageIndex: number;
  subProgress: number;
  isProcessing: boolean;
  isDone: boolean;
  pipelineError: string | null;
  uploadProgress: number;
  isUploading: boolean;

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

const INITIAL_SESSIONS: Session[] = [];

const TEXT_STAGES: PipelineStage[] = [
  { name: "Chunking transcript", weight: 10, mockDuration: 800, mockResult: "12 chunks", status: "pending" },
  { name: "Validating slides", weight: 5, mockDuration: 400, mockResult: "Slides match confirmed", status: "pending" },
  { name: "Preparing teaching context", weight: 15, mockDuration: 1500, mockResult: "Summaries ready", status: "pending" },
  { name: "Generating lecture", weight: 65, mockDuration: 4000, mockResult: "Slides + transcript ready", hasSubProgress: true, status: "pending" },
  { name: "Assembling output", weight: 5, mockDuration: 300, mockResult: "Done!", status: "pending" },
];

const VIDEO_STAGES: PipelineStage[] = [
  { name: "Transcribing lecture", weight: 12, mockDuration: 2000, mockResult: "Transcribed", status: "pending" },
  { name: "Chunking transcript", weight: 8, mockDuration: 800, mockResult: "12 chunks", status: "pending" },
  { name: "Extracting lecture slides", weight: 10, mockDuration: 1500, mockResult: "Slides extracted", status: "pending" },
  { name: "Preparing teaching context", weight: 12, mockDuration: 1500, mockResult: "Summaries ready", status: "pending" },
  { name: "Generating lecture", weight: 53, mockDuration: 4000, mockResult: "Slides + transcript ready", hasSubProgress: true, status: "pending" },
  { name: "Assembling output", weight: 5, mockDuration: 300, mockResult: "Done!", status: "pending" },
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

// Helper to get active pipeline run's state
function getActiveRun(state: AppState): PipelineRun | null {
  if (!state.activePipelineId) return null;
  return state.pipelineRuns[state.activePipelineId] || null;
}

const EMPTY_STAGES = TEXT_STAGES.map((s) => ({ ...s }));

/** Derive legacy pipeline fields from active run — call after any pipelineRuns update */
function syncLegacyFields(runs: Record<string, PipelineRun>, activeId: string | null) {
  const run = activeId ? runs[activeId] : null;
  return {
    stages: run?.stages || EMPTY_STAGES,
    currentStageIndex: run?.currentStageIndex ?? -1,
    subProgress: run?.subProgress ?? 0,
    isProcessing: run?.isProcessing ?? false,
    isDone: run?.isDone ?? false,
    pipelineError: run?.error ?? null,
    uploadProgress: run?.uploadProgress ?? 0,
    isUploading: run?.isUploading ?? false,
  };
}

export const useAppStore = create<AppState>((set, get) => {
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
  activeSessionId: null,
  loadSessions: async () => {
    try {
      const data = await fetchSessions();
      const sessions: Session[] = data.map((s) => ({
        id: s.id,
        name: s.name,
        date: new Date(s.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
        groups: 0,
      }));
      set({ sessions });
    } catch (e) {
      console.error("[Sessions] Failed to load sessions:", e);
    }
  },
  loadSession: async (sessionId: string) => {
    set({ activeSessionId: sessionId });
    const data = await fetchSession(sessionId);
    if (data) {
      get().setOutput(
        data.markdown,
        (data.concept_groups || []) as ConceptGroup[],
        (data.verification_report || []) as VerificationClaim[],
      );
    }
  },
  createNewSession: async () => {
    const result = await apiCreateSession("New Lecture");
    if (result) {
      set({ activeSessionId: result.id });
      // Add to sessions list immediately so sidebar shows it
      set((s) => ({
        sessions: [
          { id: result.id, name: result.name, date: new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }), groups: 0 },
          ...s.sessions,
        ],
      }));
      return result.id;
    }
    return null;
  },
  deleteSession: async (sessionId: string) => {
    const { deleteSession: apiDelete } = await import("./api");
    const ok = await apiDelete(sessionId);
    if (ok) {
      set((s) => ({ sessions: s.sessions.filter((sess) => sess.id !== sessionId) }));
    }
  },

  // Sidebar
  sidebarOpen: true,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),

  // Upload
  transcriptFile: null,
  videoFile: null,
  slidesFile: null,
  setTranscriptFile: (f) => set({ transcriptFile: f }),
  setVideoFile: (f) => set({ videoFile: f }),
  setSlidesFile: (f) => set({ slidesFile: f }),

  // Pipeline runs
  pipelineRuns: {},
  activePipelineId: null,

  // Legacy pipeline fields — derived from active run on each state update
  stages: EMPTY_STAGES,
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
      toast.error("No file selected");
      return;
    }

    const isVideo = /\.(mp4|mkv|avi|mov|webm)$/i.test(file.name);
    const stageTemplate = isVideo ? VIDEO_STAGES : TEXT_STAGES;
    const stages = stageTemplate.map((s) => ({ ...s, status: "pending" as const }));

    const stageMap: Record<string, number> = {};
    stages.forEach((s, i) => { stageMap[s.name] = i; });
    stageMap["Done"] = stages.length - 1;

    // Generate a temporary ID (will be replaced by fileId after upload)
    const tempId = `pending-${Date.now()}`;
    const sessionName = file.name.replace(/\.[^.]+$/, "").replace(/[-_]/g, " ");

    // If we have an active session, rename it to the file name
    const currentSessionId = get().activeSessionId;
    if (currentSessionId) {
      import("./api").then(({ renameSession }) => {
        renameSession(currentSessionId, sessionName);
      });
      // Update sidebar immediately
      set((s) => ({
        sessions: s.sessions.map((sess) =>
          sess.id === currentSessionId ? { ...sess, name: sessionName } : sess
        ),
      }));
    }

    // Create the pipeline run
    const run: PipelineRun = {
      sessionName,
      fileId: tempId,
      stages,
      currentStageIndex: -1,
      subProgress: 0,
      isProcessing: true,
      isDone: false,
      error: null,
      isUploading: true,
      uploadProgress: 0,
      cancel: null,
    };

    set((s) => ({
      pipelineRuns: { ...s.pipelineRuns, [tempId]: run },
      activePipelineId: tempId,
    }));

    (async () => {
      try {
        toast.loading("Uploading lecture...", { id: `upload-${tempId}` });

        const { file_id } = await uploadFile(file, (percent) => {
          set((s) => {
            const runs = { ...s.pipelineRuns };
            if (runs[tempId]) runs[tempId] = { ...runs[tempId], uploadProgress: percent };
            return { pipelineRuns: runs };
          });
        });

        // Upload slides PDF if provided
        const slidesFile = get().slidesFile;
        if (slidesFile) {
          toast.loading("Uploading slides...", { id: `upload-${tempId}` });
          await uploadSlides(file_id, slidesFile);
        }

        // Migrate from tempId to real fileId
        set((s) => {
          const runs = { ...s.pipelineRuns };
          const r = runs[tempId];
          if (r) {
            delete runs[tempId];
            runs[file_id] = { ...r, fileId: file_id, isUploading: false, uploadProgress: 100, currentStageIndex: 0 };
          }
          return {
            pipelineRuns: runs,
            activePipelineId: s.activePipelineId === tempId ? file_id : s.activePipelineId,
          };
        });

        toast.success("Upload complete!", { id: `upload-${tempId}` });
        toast.loading("Processing lecture...", { id: `pipeline-${file_id}` });

        const activeSession = get().activeSessionId;
        const cancelFn = runPipeline(
          file_id,
          // onUpdate
          (event: PipelineEvent) => {
            const stageIndex = event.current_stage ? (stageMap[event.current_stage] ?? -1) : -1;
            set((s) => {
              const runs = { ...s.pipelineRuns };
              const r = runs[file_id];
              if (!r) return s;
              const newStages = [...r.stages];
              for (let i = 0; i < newStages.length; i++) {
                if (i < stageIndex) newStages[i] = { ...newStages[i], status: "done" };
                else if (i === stageIndex) newStages[i] = { ...newStages[i], status: "running" };
              }
              runs[file_id] = { ...r, stages: newStages, currentStageIndex: stageIndex, subProgress: event.progress };
              return { pipelineRuns: runs };
            });
          },
          // onError
          (error) => {
            set((s) => {
              const runs = { ...s.pipelineRuns };
              const r = runs[file_id];
              if (r) runs[file_id] = { ...r, isProcessing: false, error, cancel: null };
              return { pipelineRuns: runs };
            });
            toast.error(`Pipeline failed: ${error}`, { id: `pipeline-${file_id}` });
          },
          // onDone
          async (output) => {
            toast.success("Your lecture is ready!", { id: `pipeline-${file_id}`, duration: 5000 });

            // Only set output if this is the active run
            if (output && get().activePipelineId === file_id) {
              get().setOutput(
                output.markdown,
                (output.concept_groups || []) as ConceptGroup[],
                (output.verification_report || []) as VerificationClaim[],
              );
            }

            await get().loadSessions();

            set((s) => {
              const runs = { ...s.pipelineRuns };
              const r = runs[file_id];
              if (r) {
                const doneStages = r.stages.map((st) => ({ ...st, status: "done" as const }));
                runs[file_id] = { ...r, stages: doneStages, isProcessing: false, isDone: true, cancel: null };
              }
              return { pipelineRuns: runs };
            });
          },
          activeSession || undefined,
        );

        // Store the cancel function
        set((s) => {
          const runs = { ...s.pipelineRuns };
          if (runs[file_id]) runs[file_id] = { ...runs[file_id], cancel: cancelFn };
          return { pipelineRuns: runs };
        });

      } catch (err) {
        console.error("[Pipeline] Error:", err);
        const message = err instanceof Error ? err.message : "Upload failed";
        set((s) => {
          const runs = { ...s.pipelineRuns };
          const r = runs[tempId] || runs[Object.keys(runs).find((k) => runs[k]?.sessionName === sessionName) || ""];
          if (r) {
            const key = Object.keys(runs).find((k) => runs[k] === r) || tempId;
            runs[key] = { ...r, isProcessing: false, isUploading: false, error: message };
          }
          return { pipelineRuns: runs };
        });
        toast.error(message, { id: `upload-${tempId}` });
      }
    })();
  },

  cancelPipeline: (fileId?: string) => {
    const id = fileId || get().activePipelineId;
    if (!id) return;

    const run = get().pipelineRuns[id];
    if (run?.cancel) run.cancel();

    set((s) => {
      const runs = { ...s.pipelineRuns };
      delete runs[id];
      return {
        pipelineRuns: runs,
        activePipelineId: s.activePipelineId === id ? null : s.activePipelineId,
      };
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

  // Reset — clears upload state for a new session, but keeps running pipelines alive
  reset: () => {
    set({
      transcriptFile: null,
      videoFile: null,
      slidesFile: null,
      activePipelineId: null,
      activeSessionId: null,
      markdown: "",
      groups: [],
      trustStats: { totalClaims: 0, correctClaims: 0, verifiedPercent: 0 },
    });
  },
})});

// Auto-sync legacy pipeline fields whenever pipelineRuns or activePipelineId changes
useAppStore.subscribe((state, prev) => {
  if (state.pipelineRuns !== prev.pipelineRuns || state.activePipelineId !== prev.activePipelineId) {
    const legacy = syncLegacyFields(state.pipelineRuns, state.activePipelineId);
    // Only update if values actually changed to avoid infinite loop
    if (
      state.isProcessing !== legacy.isProcessing ||
      state.isDone !== legacy.isDone ||
      state.currentStageIndex !== legacy.currentStageIndex ||
      state.subProgress !== legacy.subProgress ||
      state.pipelineError !== legacy.pipelineError ||
      state.isUploading !== legacy.isUploading ||
      state.uploadProgress !== legacy.uploadProgress
    ) {
      useAppStore.setState(legacy);
    }
  }
});
