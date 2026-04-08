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

export interface ProfessorInsight {
  instructor: string;
  has_data: boolean;
  quality?: number;
  difficulty?: number;
  num_ratings?: number;
  would_take_again?: number;
  match_score: number;
  insight: string;
  flags: string[];
}

export interface WorkloadCourse {
  course_code: string;
  instructor: string | null;
  credits: number;
  difficulty: number;
  class_hours_per_week: number;
  study_hours_per_week: number;
  total_hours_per_week: number;
}

export interface DailyLoad {
  label: string;
  class_hours: number;
  num_classes: number;
  gap_hours: number;
  is_heavy: boolean;
}

export interface WorkloadData {
  course_breakdown: WorkloadCourse[];
  daily_load: Record<string, DailyLoad>;
  total_class_hours: number;
  total_study_hours: number;
  total_weekly_hours: number;
  workload_score: number;
  warnings: string[];
  summary: string;
}

export interface ProfessorMatchData {
  professor_insights: ProfessorInsight[];
  avg_professor_score: number;
  warnings: string[];
  recommendations: string[];
}

export interface NegotiationTrade {
  action: string;
  constraint: string;
  impact: string;
  sections_gained: number;
}

export interface NegotiationData {
  bottlenecks: { constraint: string; detail: string; severity: string }[];
  trades: NegotiationTrade[];
  zero_candidate_requirements: string[];
  analysis: string;
}

export interface SemesterCourse {
  id: string;
  requirement: string;
  credits: number;
  category: string;
  course: string;
}

export interface SemesterPlan {
  semester: string;
  courses: SemesterCourse[];
  credits: number;
  notes: string[];
}

export interface MultiSemesterResult {
  prerequisite_analysis: {
    ready_now: string[];
    blocked: { id: string; waiting_on: string[] }[];
    chains: string[][];
  };
  rotation_analysis: {
    fall_only: { id: string; course: string }[];
    spring_only: { id: string; course: string }[];
    schedule_critical: { id: string; course: string; must_take: string }[];
  };
  semester_plan: SemesterPlan[];
  total_credits_planned: number;
  graduation_on_track: boolean;
  agents_used: string[];
  orchestration_ms: number;
}

export interface GenerateSchedulesResponse {
  schedules: ScheduleOption[];
  solver_stats: {
    solver_duration_ms: number;
    total_duration_ms: number;
    schedules_returned: number;
    orchestration_ms?: number;
  };
  professor_data?: ProfessorMatchData[];
  workload_data?: WorkloadData[];
  negotiation?: NegotiationData;
  agents_run?: string[];
}
