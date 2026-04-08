import { create } from "zustand";
import type { DegreeAudit, ProfessorRatings, ScheduleOption, SchedulePreferences } from "./types";

interface PathfinderState {
  audit: DegreeAudit | null;
  setAudit: (audit: DegreeAudit) => void;

  preferences: SchedulePreferences;
  setPreferences: (preferences: SchedulePreferences) => void;

  schedules: ScheduleOption[] | null;
  setSchedules: (schedules: ScheduleOption[]) => void;

  solverStats: Record<string, number> | null;
  setSolverStats: (stats: Record<string, number>) => void;

  professorRatings: ProfessorRatings;
  setProfessorRatings: (ratings: ProfessorRatings) => void;
  rateProfessor: (name: string, quality: number, difficulty: number) => void;

  loading: boolean;
  setLoading: (loading: boolean) => void;

  error: string | null;
  setError: (error: string | null) => void;
}

export const useStore = create<PathfinderState>((set) => ({
  audit: null,
  setAudit: (audit) => set({ audit, error: null }),

  preferences: {
    target_credits: 15,
    blocked_days: [],
    no_earlier_than: null,
    no_later_than: null,
    preferred_instructors: [],
    avoided_instructors: [],
    free_text: "",
    selected_requirement_ids: [],
  },
  setPreferences: (preferences) => set({ preferences }),

  schedules: null,
  setSchedules: (schedules) => set({ schedules }),

  solverStats: null,
  setSolverStats: (solverStats) => set({ solverStats }),

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
}));
