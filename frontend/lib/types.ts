export interface Meeting {
  days: ("M" | "T" | "W" | "R" | "F")[];
  start: string;
  end: string;
  building: string | null;
  room: string | null;
}

export interface Section {
  crn: string;
  subject: string;
  course_number: string;
  course_code: string;
  title: string;
  section: string;
  credits: number;
  instructor: string | null;
  meetings: Meeting[];
  seats_open: number;
  seats_total: number;
  waitlist_open: number;
  waitlist_total: number;
  is_full: boolean;
  is_async: boolean;
  schedule_type: string;
  term: string;
  start_date?: string;
  end_date?: string;
}

export interface CompletedRequirement {
  requirement: string;
  course: string;
  grade: string;
  credits: number;
  term: string;
}

export interface OutstandingRequirement {
  id: string;
  requirement: string;
  rule_type: "specific_course" | "choose_one_of" | "wildcard" | "course_with_lab";
  options: string[];
  pattern: string | null;
  pairs?: string[][] | null;
  credits_needed: number;
  category: "general_education" | "business_core" | "major" | "elective" | "minor";
}

export interface DegreeAudit {
  student_id: string;
  name: string;
  major: string;
  expected_graduation: string;
  credits_earned_or_inprogress: number;
  credits_required: number;
  completed_requirements: CompletedRequirement[];
  in_progress_requirements: CompletedRequirement[];
  outstanding_requirements: OutstandingRequirement[];
}

export interface SchedulePreferences {
  target_credits: number;
  blocked_days: ("M" | "T" | "W" | "R" | "F")[];
  no_earlier_than: string | null;
  no_later_than: string | null;
  preferred_instructors: string[];
  avoided_instructors: string[];
  free_text: string;
  selected_requirement_ids: string[];
}

export interface ScheduleOption {
  rank: number;
  sections: Section[];
  requirements_satisfied: string[];
  total_credits: number;
  days_off: string[];
  earliest_class: string;
  latest_class: string;
  score: number;
  explanation: string;
}

export interface ProfessorRating {
  quality: number;
  difficulty: number;
  num_ratings: number;
  would_take_again: number;
}

export type ProfessorRatings = Record<string, ProfessorRating>;

export interface GenerateSchedulesResponse {
  schedules: ScheduleOption[];
  solver_stats: {
    solver_duration_ms: number;
    total_duration_ms: number;
    schedules_returned: number;
  };
}
