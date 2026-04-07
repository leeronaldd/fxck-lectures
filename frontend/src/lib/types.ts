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
