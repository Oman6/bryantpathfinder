import { create } from "zustand";
import type {
  DegreeAudit,
  GenerateSchedulesResponse,
  GradeDistributions,
  NegotiationData,
  ProfessorMatchData,
  ProfessorRatings,
  ScheduleOption,
  SchedulePreferences,
  WorkloadData,
} from "./types";

interface PathfinderState {
  audit: DegreeAudit | null;
  setAudit: (audit: DegreeAudit) => void;

  preferences: SchedulePreferences;
  setPreferences: (preferences: SchedulePreferences) => void;

  schedules: ScheduleOption[] | null;
  setSchedules: (schedules: ScheduleOption[]) => void;

  solverStats: Record<string, number> | null;
  setSolverStats: (stats: Record<string, number>) => void;

  professorData: ProfessorMatchData[] | null;
  setProfessorData: (data: ProfessorMatchData[] | null) => void;

  workloadData: WorkloadData[] | null;
  setWorkloadData: (data: WorkloadData[] | null) => void;

  negotiation: NegotiationData | null;
  setNegotiation: (data: NegotiationData | null) => void;

  agentsRun: string[];
  setAgentsRun: (agents: string[]) => void;

  professorRatings: ProfessorRatings;
  setProfessorRatings: (ratings: ProfessorRatings) => void;
  rateProfessor: (name: string, quality: number, difficulty: number) => void;

  gradeDistributions: GradeDistributions;
  setGradeDistributions: (data: GradeDistributions) => void;

  pinnedCrns: string[];
  togglePinnedCrn: (crn: string) => void;
  clearPinnedCrns: () => void;

  loading: boolean;
  setLoading: (loading: boolean) => void;

  error: string | null;
  setError: (error: string | null) => void;

  reset: () => void;
}

const DEFAULT_PREFERENCES: SchedulePreferences = {
  target_credits: 15,
  blocked_days: [],
  no_earlier_than: null,
  no_later_than: null,
  preferred_instructors: [],
  avoided_instructors: [],
  free_text: "",
  selected_requirement_ids: [],
};

export const useStore = create<PathfinderState>((set) => ({
  audit: null,
  setAudit: (audit) => set({ audit, error: null }),

  preferences: { ...DEFAULT_PREFERENCES },
  setPreferences: (preferences) => set({ preferences }),

  schedules: null,
  setSchedules: (schedules) => set({ schedules }),

  solverStats: null,
  setSolverStats: (solverStats) => set({ solverStats }),

  professorData: null,
  setProfessorData: (professorData) => set({ professorData }),

  workloadData: null,
  setWorkloadData: (workloadData) => set({ workloadData }),

  negotiation: null,
  setNegotiation: (negotiation) => set({ negotiation }),

  agentsRun: [],
  setAgentsRun: (agentsRun) => set({ agentsRun }),

  gradeDistributions: {},
  setGradeDistributions: (gradeDistributions) => set({ gradeDistributions }),

  pinnedCrns: [],
  togglePinnedCrn: (crn) =>
    set((state) => ({
      pinnedCrns: state.pinnedCrns.includes(crn)
        ? state.pinnedCrns.filter((c) => c !== crn)
        : [...state.pinnedCrns, crn],
    })),
  clearPinnedCrns: () => set({ pinnedCrns: [] }),

  professorRatings: {},
  setProfessorRatings: (professorRatings) => set({ professorRatings }),
  rateProfessor: (name, quality, difficulty) =>
    set((state) => {
      const existing = state.professorRatings[name];
      const prev_n = existing?.num_ratings ?? 0;
      const prev_q = existing?.quality ?? 0;
      const prev_d = existing?.difficulty ?? 0;
      const new_n = prev_n + 1;
      return {
        professorRatings: {
          ...state.professorRatings,
          [name]: {
            quality: Math.round(((prev_q * prev_n + quality) / new_n) * 10) / 10,
            difficulty: Math.round(((prev_d * prev_n + difficulty) / new_n) * 10) / 10,
            num_ratings: new_n,
            would_take_again: existing?.would_take_again ?? -1,
          },
        },
      };
    }),

  loading: false,
  setLoading: (loading) => set({ loading }),

  error: null,
  setError: (error) => set({ error }),

  // Clears session state but preserves professorRatings (durable user data).
  reset: () =>
    set({
      audit: null,
      preferences: { ...DEFAULT_PREFERENCES },
      schedules: null,
      solverStats: null,
      professorData: null,
      workloadData: null,
      negotiation: null,
      agentsRun: [],
      loading: false,
      error: null,
    }),
}));
