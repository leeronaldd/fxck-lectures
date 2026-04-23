import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { toast } from "sonner";
import { ConceptGroup, VerificationClaim, TrustStats, LectureScore } from "./types";
import { computeTrustStats } from "./data";
import { uploadFile, uploadSlides, runPipeline, fetchSessions, fetchSession, createSession as apiCreateSession } from "./api";
import type { PipelineEvent, StreamedSection } from "./api";
import type { SlideCard, TranscriptSection } from "./types";

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
  createdAt?: string;  // ISO timestamp for staleness checks
  groups: number;
  status?: "pending" | "processing" | "ready" | "failed";
  errorMessage?: string | null;
  // Current pipeline stage name (e.g. "Transcribing lecture", "Generating
  // lecture", "Verifying coverage"). Populated by the backend while a run
  // is in-flight so a reloaded reader can show the user which step the
  // pipeline is on. Null when the run is done.
  currentStage?: string | null;
}

// Per-session pipeline state for concurrent processing
export interface PipelineRun {
  sessionName: string;
  fileId: string;
  sessionId?: string;          // Supabase session ID linked to this run
  stages: PipelineStage[];
  currentStageIndex: number;
  subProgress: number;
  isProcessing: boolean;
  isDone: boolean;
  error: string | null;
  isUploading: boolean;
  uploadProgress: number;
  cancel: (() => void) | null;
  // Progressive-render state: sections as they stream in from Pro. Reader
  // shows these while pipeline is still running; once isDone fires, the
  // canonical markdown from the final 'done' event takes over.
  streamingSlides: SlideCard[];
  streamingTranscript: TranscriptSection[];
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
  slidesFiles: File[];
  setTranscriptFile: (f: File | null) => void;
  setVideoFile: (f: File | null) => void;
  setSlidesFile: (f: File | null) => void;
  setSlidesFiles: (files: File[]) => void;

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
  lectureScore: LectureScore | null;
  setOutput: (md: string, groups: ConceptGroup[], claims: VerificationClaim[]) => void;
  setLectureScore: (score: LectureScore | null) => void;

  // Settings
  settings: AppSettings;
  updateSettings: (partial: Partial<AppSettings>) => void;

  // Reset
  reset: () => void;
}

const INITIAL_SESSIONS: Session[] = [];

const TEXT_STAGES: PipelineStage[] = [
  { name: "Chunking transcript", weight: 8, mockDuration: 800, mockResult: "12 chunks", status: "pending" },
  { name: "Validating slides", weight: 5, mockDuration: 400, mockResult: "Slides match confirmed", status: "pending" },
  { name: "Describing slides", weight: 8, mockDuration: 1500, mockResult: "Slides described", status: "pending" },
  { name: "Planning lecture structure", weight: 15, mockDuration: 2500, mockResult: "Teaching plan ready", status: "pending" },
  { name: "Generating lecture", weight: 59, mockDuration: 4000, mockResult: "Slides + transcript ready", hasSubProgress: true, status: "pending" },
  { name: "Assembling output", weight: 5, mockDuration: 300, mockResult: "Done!", status: "pending" },
];

const VIDEO_STAGES: PipelineStage[] = [
  { name: "Transcribing lecture", weight: 15, mockDuration: 3000, mockResult: "Transcribed", status: "pending" },
  { name: "Chunking transcript", weight: 5, mockDuration: 800, mockResult: "12 chunks", status: "pending" },
  { name: "Extracting lecture slides", weight: 5, mockDuration: 1500, mockResult: "Slides extracted", status: "pending" },
  { name: "Describing slides", weight: 5, mockDuration: 1500, mockResult: "Slides described", status: "pending" },
  { name: "Planning lecture structure", weight: 15, mockDuration: 2500, mockResult: "Teaching plan ready", status: "pending" },
  { name: "Generating lecture", weight: 50, mockDuration: 4000, mockResult: "Slides + transcript ready", hasSubProgress: true, status: "pending" },
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

export const useAppStore = create<AppState>()(persist((set, get) => {
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
        createdAt: s.created_at,
        groups: 0,
        status: (s.status as Session["status"]) ?? "ready",
        errorMessage: s.error_message ?? null,
        currentStage: s.current_stage ?? null,
      }));
      set({ sessions });
    } catch (e) {
      console.error("[Sessions] Failed to load sessions:", e);
    }
  },
  loadSession: async (sessionId: string) => {
    set({ activeSessionId: sessionId });
    // Clear any stale lecture score from the previously-viewed session.
    // Scores aren't persisted server-side yet, so they only exist in-memory
    // for runs completed in the current browser tab.
    get().setLectureScore(null);
    const data = await fetchSession(sessionId);
    if (data) {
      get().setOutput(
        data.markdown,
        (data.concept_groups || []) as ConceptGroup[],
        (data.verification_report || []) as VerificationClaim[],
      );
      // Mirror status + current stage into the sessions list so the reader
      // can react to processing/failed and show the pipeline stage without
      // a second round-trip.
      const status = (data.status as Session["status"]) ?? "ready";
      const errorMessage = data.error_message ?? null;
      const currentStage = data.current_stage ?? null;
      set((s) => ({
        sessions: s.sessions.map((sess) =>
          sess.id === sessionId ? { ...sess, status, errorMessage, currentStage } : sess
        ),
      }));
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
  slidesFiles: [],
  setTranscriptFile: (f) => set({ transcriptFile: f }),
  setVideoFile: (f) => set({ videoFile: f }),
  setSlidesFile: (f) => set({ slidesFile: f, slidesFiles: f ? [f] : [] }),
  setSlidesFiles: (files) => set({ slidesFiles: files, slidesFile: files[0] || null }),

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

    const isVideo = /\.(mp4|mkv|avi|mov|webm|mp3|m4a|wav)$/i.test(file.name);
    const stageTemplate = isVideo ? VIDEO_STAGES : TEXT_STAGES;
    const stages = stageTemplate.map((s) => ({ ...s, status: "pending" as const }));

    const stageMap: Record<string, number> = {};
    stages.forEach((s, i) => { stageMap[s.name] = i; });
    stageMap["Done"] = stages.length - 1;
    // Aliases: backend sometimes sends different names for the same stage
    stageMap["Extracting slides from PDF"] = stageMap["Extracting lecture slides"] ?? stageMap["Describing slides"] ?? 2;
    stageMap["Validating slides"] = stageMap["Validating slides"] ?? stageMap["Extracting lecture slides"] ?? 2;
    stageMap["Preparing teaching context"] = stageMap["Planning lecture structure"] ?? 3;

    // Generate a temporary ID (will be replaced by fileId after upload)
    const tempId = `pending-${Date.now()}`;
    const sessionName = file.name.replace(/\.[^.]+$/, "").replace(/[-_]/g, " ");

    // Rename active session to file name if one exists
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
      sessionId: currentSessionId || undefined,
      stages,
      currentStageIndex: -1,
      subProgress: 0,
      isProcessing: true,
      isDone: false,
      error: null,
      isUploading: true,
      uploadProgress: 0,
      cancel: null,
      streamingSlides: [],
      streamingTranscript: [],
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

        // Upload slides PDFs if provided (non-fatal — pipeline runs without slides)
        const slidesFiles = get().slidesFiles;
        if (slidesFiles.length > 0) {
          try {
            toast.loading(`Uploading ${slidesFiles.length} slide file${slidesFiles.length > 1 ? "s" : ""}...`, { id: `upload-${tempId}` });
            for (const sf of slidesFiles) {
              await uploadSlides(file_id, sf);
            }
          } catch (err) {
            console.warn("[Pipeline] Slides upload failed, continuing without slides:", err);
          }
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

        // Ensure a session exists so the backend can PATCH it with the result.
        // Without this, session_id is null and the backend creates a duplicate row.
        let activeSession = get().activeSessionId;
        if (!activeSession) {
          const created = await apiCreateSession(sessionName);
          if (created) {
            activeSession = created.id;
            set((s) => ({
              activeSessionId: created.id,
              sessions: [
                { id: created.id, name: sessionName, date: new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }), groups: 0, status: "pending" },
                ...s.sessions,
              ],
            }));
            // Update the pipeline run with the new session ID
            set((s) => {
              const runs = { ...s.pipelineRuns };
              const r = runs[file_id];
              if (r) runs[file_id] = { ...r, sessionId: created.id };
              return { pipelineRuns: runs };
            });
          }
        }

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
            import("@/lib/analytics").then(({ trackEvent }) =>
              trackEvent("upload_failed", { file_id, error })
            );
          },
          // onDone
          async (output) => {
            toast.success("Your lecture is ready!", { id: `pipeline-${file_id}`, duration: 5000 });
            import("@/lib/analytics").then(({ trackEvent }) =>
              trackEvent("upload_complete", { file_id })
            );

            // Only set output if this is the active run
            if (output && get().activePipelineId === file_id) {
              get().setOutput(
                output.markdown,
                (output.concept_groups || []) as ConceptGroup[],
                (output.verification_report || []) as VerificationClaim[],
              );
              get().setLectureScore((output.lecture_score ?? null) as LectureScore | null);
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
          // onSection — progressive rendering. Append each section to the
          // run's streaming arrays; reader reads from these while the run
          // is in flight. Replace any existing entry at the same index to
          // allow late-arriving slide metadata to upgrade a section.
          (section: StreamedSection) => {
            set((s) => {
              const runs = { ...s.pipelineRuns };
              const r = runs[file_id];
              if (!r) return s;
              const slides = [...r.streamingSlides];
              const transcript = [...r.streamingTranscript];
              const existingIdx = transcript.findIndex(
                (t) => t.slide_number === section.transcript.slide_number
              );
              if (existingIdx >= 0) {
                transcript[existingIdx] = section.transcript;
                // Update or add matching slide
                const slideIdx = slides.findIndex((sl) => sl.slide_id === section.slide.slide_id);
                if (slideIdx >= 0) slides[slideIdx] = section.slide;
                else slides.push(section.slide);
              } else {
                transcript.push(section.transcript);
                slides.push(section.slide);
              }
              runs[file_id] = { ...r, streamingSlides: slides, streamingTranscript: transcript };
              return { pipelineRuns: runs };
            });
          },
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
  lectureScore: null,
  setOutput: (md, groups, claims) =>
    set({
      markdown: md,
      groups,
      trustStats: computeTrustStats(claims),
    }),
  setLectureScore: (score) => set({ lectureScore: score }),

  // Settings
  settings: { ...DEFAULT_SETTINGS },
  updateSettings: (partial) =>
    set((state) => ({ settings: { ...state.settings, ...partial } })),

  // Reset — clears upload state for a new session. Drops stale finished/errored
  // pipeline runs so they can't hijack /upload via the sidebar's Processing
  // section. Genuinely in-flight runs (isProcessing && !isDone && !error) are
  // preserved so a background SSE stream isn't orphaned.
  reset: () => {
    set((s) => {
      const runs: Record<string, PipelineRun> = {};
      for (const [id, run] of Object.entries(s.pipelineRuns)) {
        if (run.isProcessing && !run.isDone && !run.error) runs[id] = run;
      }
      return {
        transcriptFile: null,
        videoFile: null,
        slidesFile: null,
        slidesFiles: [],
        pipelineRuns: runs,
        activePipelineId: null,
        activeSessionId: null,
        markdown: "",
        groups: [],
        trustStats: { totalClaims: 0, correctClaims: 0, verifiedPercent: 0 },
        lectureScore: null,
      };
    });
  },
  });
}, {
  name: "klare-pipeline-state",
  storage: createJSONStorage(() => localStorage),
  // Only persist pipeline progress so F5 mid-run keeps the stepper visible.
  // Anything derived (user, sessions, upload File objects) is re-fetched or re-uploaded.
  partialize: (state) => ({
    pipelineRuns: state.pipelineRuns,
    activePipelineId: state.activePipelineId,
  }),
  // Strip any stale upload-in-progress state when rehydrating — a reloaded tab
  // has no active XHR, so showing "Uploading 87%" would be a lie. Anything
  // that was mid-upload is treated as cancelled on refresh.
  onRehydrateStorage: () => (state) => {
    if (!state) return;
    const runs = { ...state.pipelineRuns };
    let changed = false;
    for (const [id, run] of Object.entries(runs)) {
      if (run.isUploading) {
        delete runs[id];
        changed = true;
      }
    }
    if (changed) {
      state.pipelineRuns = runs;
      if (state.activePipelineId && !runs[state.activePipelineId]) {
        state.activePipelineId = null;
      }
    }
  },
}));

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
