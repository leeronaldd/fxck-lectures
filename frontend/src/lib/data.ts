import { ConceptGroup, VerificationClaim, TrustStats } from "./types";

export async function getMarkdownContent(): Promise<string> {
  const res = await fetch("/data/v4_lecture_replacement.md");
  return res.text();
}

export async function getConceptGroups(): Promise<ConceptGroup[]> {
  const res = await fetch("/data/v4_concept_groups.json");
  return res.json();
}

export async function getVerificationReport(): Promise<VerificationClaim[]> {
  const res = await fetch("/data/v4_verification_report.json");
  return res.json();
}

export function computeTrustStats(rawClaims: VerificationClaim[] | Record<string, unknown>): TrustStats {
  // Handle both flat array and {claims: [...], textbook_sources: [...]} formats
  const claims: VerificationClaim[] = Array.isArray(rawClaims)
    ? rawClaims
    : Array.isArray((rawClaims as Record<string, unknown>)?.claims)
      ? (rawClaims as Record<string, unknown>).claims as VerificationClaim[]
      : [];
  const totalClaims = claims.length;
  const correctClaims = claims.filter((c) => c.verdict === "correct").length;
  const verifiedPercent =
    totalClaims > 0 ? Math.round((correctClaims / totalClaims) * 100) : 0;
  return { totalClaims, correctClaims, verifiedPercent };
}

export function getCIColor(ci: number): string {
  if (ci >= 80) return "var(--ci-critical)";
  if (ci >= 50) return "var(--ci-high)";
  if (ci >= 20) return "var(--ci-medium)";
  return "var(--ci-low)";
}

export function getCILabel(ci: number): string {
  if (ci >= 80) return "Must study";
  if (ci >= 50) return "Important";
  if (ci >= 20) return "Low priority";
  return "Skip";
}
