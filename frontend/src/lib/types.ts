export interface ConceptGroup {
  group_index: number;
  group_name: string;
  chunk_indices: number[];
  action: "generate" | "skip" | "minimal";
  ci_percent: number;
  skip_message: string;
  key_terms: string[];
  prerequisites: string[];
  expansion_hints: string[];
  needs_expansion: boolean;
  emphasis_score: "HIGH" | "MEDIUM" | "LOW";
  raw_transcript_length: number;
}

export interface VerificationClaim {
  claim: string;
  claim_type: string;
  source_group: string;
  verdict: "correct" | "wrong";
  correction: string;
  sources: string[] | null;
  exam_relevant: boolean;
  exam_notes: string;
}

export interface TrustStats {
  totalClaims: number;
  correctClaims: number;
  verifiedPercent: number;
}

// V2 types
export interface SlideCard {
  slide_id: string;
  title: string;
  card_type: "professor_slide" | "diagram";
  image_ref: string;
  bullet_points: string[];
  exam_tip: string;
  ei_percent: number;
}

export interface TranscriptSection {
  slide_number: number;
  title: string;
  narrative: string;
  ei_percent: number;
  ei_reasoning: string;
}

// Flash's honest assessment of the lecture — shown as a shareable card at
// the end of the reader. Produced by the completeness checker (one Flash
// call does both missed-item audit + score). null when Flash failed or
// when an older session's payload doesn't have the field.
export type LectureScoreLabel = "rough" | "ok" | "good" | "great" | "excellent";

export interface LectureScore {
  overall: number;           // 0-100
  clarity: number;           // 0-100
  focus: number;             // 0-100
  efficiency: number;        // 0-100
  label: LectureScoreLabel;
  comment: string;           // One-line personalised observation
  time_saved_min: number;    // Minutes Klare saved the student
}
