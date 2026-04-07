"""Completeness Checker: grep-based coverage check for Stage 2 output.

Checks that key terms from Stage 1 chunks appear in the generated explanations.
Misses are categorized by CI% and either:
- High CI%: patched via targeted LLM follow-up (insert missing term)
- Low CI%: inline skip-line inserted at end of relevant section
"""

import json
import re
from dataclasses import dataclass, asdict

from src.config import GCP_PROJECT_ID, GCP_LOCATION, CHUNKER_FALLBACK_MODEL, GENERATOR_MODEL


# ---------------------------------------------------------------------------
# General-purpose noise term filter
# Works across any lecture transcript, not just microbiology
# ---------------------------------------------------------------------------

# Filler words that start sentence fragments from auto-captions
_NOISE_PREFIXES = (
    "so ", "but ", "um ", "uh ", "the ", "and ", "although ",
    "okay ", "now ", "well ", "like ", "just ", "yeah ", "right ",
    "basically ", "obviously ", "actually ", "did ", "does ", "do ",
    "if ", "when ", "where ", "what ", "how ", "why ", "are ", "is ",
)

# Patterns that indicate a term is a transcript fragment, not real vocabulary
_NOISE_PATTERNS = re.compile(
    r"which which|"       # stuttered repetition
    r"has also|"          # sentence fragment
    r"virus have|"        # garbled grammar
    r"virus is\b|"        # "noro virus is" — fragment
    r"classifi |"         # cut-off word
    r"the the|"           # repeated article
    r" a virus$|"         # "um a virus" fragment
    r"^\w+ \w+ \w+ \w+",  # 4+ words = almost always a fragment
    re.IGNORECASE,
)


def _is_noise_term(term: str) -> bool:
    """Detect whether a 'key term' is actually transcript garbage.

    General-purpose: works across any lecture, not hardcoded to specific terms.
    Real scientific terms are 1-3 word proper vocabulary.
    Noise terms are sentence fragments, filler, stutters, or garbled auto-captions.
    """
    if not term or len(term) < 3:
        return True

    # Too many words = sentence fragment
    if len(term.split()) > 3:
        return True

    # Starts with filler word
    if any(term.startswith(p) for p in _NOISE_PREFIXES):
        return True

    # Matches known garbage patterns
    if _NOISE_PATTERNS.search(term):
        return True

    # Contains repeated words ("virus virus", "the the")
    words = term.split()
    if len(words) >= 2 and len(set(words)) < len(words):
        return True

    # All lowercase multi-word terms where every word is a common English word
    # (real terms have at least one technical/scientific word)
    _COMMON_WORDS = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "can", "could", "may", "might", "shall", "should", "must",
        "not", "no", "nor", "but", "and", "or", "so", "if", "then",
        "also", "just", "only", "very", "most", "some", "all", "both",
        "it", "its", "they", "them", "we", "our", "you", "your",
        "this", "that", "these", "those", "here", "there", "now",
        "what", "which", "who", "how", "when", "where", "why",
    }
    if len(words) >= 2 and all(w in _COMMON_WORDS for w in words):
        return True

    return False


@dataclass
class MissReport:
    term: str
    ci_percent: int
    source_group: str           # which concept group should have covered this
    action: str                 # "regeneration_target" or "inline_skip"
    skip_line: str = ""         # the inline skip text to insert


def extract_slide_terms(screenshots: list[dict]) -> list[dict]:
    """Extract key scientific terms from slide descriptions using Gemini Flash.

    Catches content on slides but not in the spoken transcript.
    Uses Flash instead of hardcoded patterns — works for ANY medical discipline.
    Cost: ~200 tokens for one batched call.

    Returns list of {"term": str, "source_slide": str, "ci_percent": int}.
    """
    if not screenshots:
        return []

    # Batch all slide descriptions into one Flash call
    slide_descs = []
    for ss in screenshots:
        desc = ss.get("description", "").strip()
        img = ss.get("image_filename", "unknown")
        if desc and "black screen" not in desc.lower() and "no visible" not in desc.lower():
            slide_descs.append(f"Slide {img}: {desc[:200]}")

    if not slide_descs:
        return []

    try:
        from google import genai
        import json as _json

        prompt = (
            "From these lecture slide descriptions, extract any medical techniques, "
            "tests, procedures, lab methods, diagnostic tools, or scientific frameworks "
            "that a student might need to know for an exam.\n\n"
            "For each term, estimate its exam importance (0-100).\n\n"
            "Return ONLY a JSON array:\n"
            '[{"term": "plaque assay", "ci_percent": 40}, {"term": "RT-PCR", "ci_percent": 40}]\n\n'
            "SLIDE DESCRIPTIONS:\n" + "\n".join(slide_descs)
        )

        client = genai.Client(
            vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION
        )
        response = client.models.generate_content(
            model=CHUNKER_FALLBACK_MODEL,
            contents=prompt,
            config={"temperature": 0.1, "max_output_tokens": 1024},
        )

        from src.json_repair import extract_json
        raw_terms = extract_json(response.text, expect_array=True)

        seen = set()
        unique = []
        for t in raw_terms:
            term = t.get("term", "").strip()
            key = term.lower()
            if key and key not in seen and len(term) > 2:
                seen.add(key)
                unique.append({
                    "term": term,
                    "source_slide": "slides",
                    "ci_percent": min(100, max(0, int(t.get("ci_percent", 35)))),
                })

        return unique

    except Exception as e:
        print(f"  Warning: Flash slide term extraction failed: {e}")
        return []


def check_completeness(
    explanations: list[dict],
    groups: list,
    ci_threshold: int = 50,
    screenshots: list[dict] | None = None,
) -> list[MissReport]:
    """Check which key terms from concept groups are missing from output.

    Args:
        explanations: list of Explanation dicts (from Stage 2 output)
        groups: list of ConceptGroup instances
        ci_threshold: terms with CI% above this → regeneration target, below → inline skip
        screenshots: optional list of screenshot dicts — extracts slide-only terms

    Returns:
        List of MissReport for each missing term.
    """
    # Build the full output text (all explanations concatenated)
    full_text = " ".join(
        e.get("explanation_text", "") for e in explanations
        if not e.get("was_skipped", False)
    ).lower()

    misses = []

    # --- Check key terms from concept groups ---
    for group in groups:
        # Skip groups that were skipped (their terms are intentionally absent)
        if group.action == "skip":
            continue

        for term in group.key_terms:
            term_lower = term.lower().strip()
            if _is_noise_term(term_lower):
                continue

            # Check for the term in the output
            # Use word boundary matching to avoid false positives
            # But also check without boundaries for compound terms
            found = False

            # Exact match
            if term_lower in full_text:
                found = True

            # Try without hyphens/spaces for compound terms
            if not found:
                normalized = re.sub(r'[\s-]+', '', term_lower)
                if len(normalized) > 4 and normalized in re.sub(r'[\s-]+', '', full_text):
                    found = True

            if not found:
                ci = group.ci_percent
                if ci > ci_threshold:
                    misses.append(MissReport(
                        term=term,
                        ci_percent=ci,
                        source_group=group.group_name,
                        action="regeneration_target",
                    ))
                else:
                    skip_line = f"**{term}** — mentioned in lecture, low priority (CI% {ci}%). Expand?"
                    misses.append(MissReport(
                        term=term,
                        ci_percent=ci,
                        source_group=group.group_name,
                        action="inline_skip",
                        skip_line=skip_line,
                    ))

    # --- Check slide-only terms (content on slides but not in transcript) ---
    if screenshots:
        slide_terms = extract_slide_terms(screenshots)
        for st in slide_terms:
            term_lower = st["term"].lower()
            found = term_lower in full_text
            if not found:
                normalized = re.sub(r'[\s-]+', '', term_lower)
                if len(normalized) > 3 and normalized in re.sub(r'[\s-]+', '', full_text):
                    found = True
            if not found:
                ci = st["ci_percent"]
                skip_line = (
                    f"**{st['term']}** 🟡 — shown on lecture slide but not covered above. "
                    f"Low priority (CI% {ci}%). Expand?"
                )
                misses.append(MissReport(
                    term=st["term"],
                    ci_percent=ci,
                    source_group=f"Slide: {st['source_slide']}",
                    action="inline_skip",
                    skip_line=skip_line,
                ))

    return misses


def format_report(misses: list[MissReport]) -> str:
    """Format the miss report as human-readable text."""
    if not misses:
        return "All key terms covered. No misses detected."

    regen = [m for m in misses if m.action == "regeneration_target"]
    skips = [m for m in misses if m.action == "inline_skip"]

    lines = [f"Completeness Check: {len(misses)} terms missing\n"]

    if regen:
        lines.append(f"REGENERATION TARGETS ({len(regen)} high-priority misses):")
        for m in sorted(regen, key=lambda x: -x.ci_percent):
            lines.append(f"  - {m.term} (CI% {m.ci_percent}%) — should be in: {m.source_group}")

    if skips:
        lines.append(f"\nINLINE SKIPS ({len(skips)} low-priority misses):")
        for m in sorted(skips, key=lambda x: -x.ci_percent):
            lines.append(f"  - {m.skip_line}")

    return "\n".join(lines)


def save_report(misses: list[MissReport], output_path: str):
    """Save miss report to JSON."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([asdict(m) for m in misses], f, indent=2, ensure_ascii=False)
    print(f"Saved completeness report ({len(misses)} misses) to {output_path}")


# ---------------------------------------------------------------------------
# Auto-fix: patch high-CI% misses via targeted LLM follow-up
# ---------------------------------------------------------------------------

PATCH_PROMPT = """The following exam-testable terms were described conceptually in a student explanation but the actual scientific vocabulary was never used. The student needs these exact terms for their exam.

MISSING TERMS: {terms}

CURRENT EXPLANATION TEXT:
\"\"\"
{explanation_text}
\"\"\"

For each missing term, find the sentence where the concept is already described and insert the bolded term naturally. For example, if "budding" is missing and the text says "it pushes its way out, wrapping itself in host membrane," change it to "it pushes its way out in a process called **budding**, wrapping itself in host membrane."

Return ONLY the updated explanation text. Do not add new content — just insert the missing term names at the right points. Keep everything else identical."""


def patch_regeneration_targets(
    explanations: list[dict],
    misses: list[MissReport],
    groups: list,
) -> list[dict]:
    """Patch high-CI% missing terms into explanations via targeted LLM calls.

    Groups regeneration targets by their source group, then sends one
    targeted follow-up prompt per affected explanation.

    Returns updated explanations list.
    """
    regen_misses = [m for m in misses if m.action == "regeneration_target"]
    if not regen_misses:
        return explanations

    # Group misses by source_group
    by_group: dict[str, list[str]] = {}
    for m in regen_misses:
        by_group.setdefault(m.source_group, []).append(m.term)

    # Filter to real terms (skip transcript garbage)
    # Use general-purpose noise filter

    from google import genai
    client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)

    for group_name, terms in by_group.items():
        # Filter noise
        real_terms = [t for t in terms if not _is_noise_term(t.lower())]
        if not real_terms:
            continue

        # Find the matching explanation
        expl = None
        for e in explanations:
            if e.get("topic_name") == group_name and not e.get("was_skipped"):
                expl = e
                break

        if not expl or not expl.get("explanation_text"):
            continue

        print(f"  Patching {len(real_terms)} terms into: {group_name}")
        print(f"    Terms: {', '.join(real_terms)}")

        prompt = PATCH_PROMPT.format(
            terms=", ".join(real_terms),
            explanation_text=expl["explanation_text"],
        )

        try:
            response = client.models.generate_content(
                model=CHUNKER_FALLBACK_MODEL,
                contents=prompt,
                config={"temperature": 0.2, "max_output_tokens": 8192},
            )
            patched_text = response.text.strip()

            # Verify the patch actually contains the terms
            patched_lower = patched_text.lower()
            terms_found = sum(1 for t in real_terms if t.lower() in patched_lower)
            if terms_found >= len(real_terms) * 0.5:  # at least half the terms made it
                expl["explanation_text"] = patched_text
                expl["word_count"] = len(patched_text.split())
                print(f"    Patched: {terms_found}/{len(real_terms)} terms inserted")
            else:
                print(f"    Patch rejected: only {terms_found}/{len(real_terms)} terms found in output")
        except Exception as e:
            print(f"    Patch failed: {e}")

    return explanations


# ---------------------------------------------------------------------------
# Auto-fix: insert inline skip-lines for low-CI% misses
# ---------------------------------------------------------------------------

def insert_inline_skips(
    explanations: list[dict],
    misses: list[MissReport],
    groups: list,
) -> list[dict]:
    """Insert inline skip-lines for low-CI% missing terms.

    Appends skip-lines at the end of the relevant explanation section.

    Returns updated explanations list.
    """
    skip_misses = [m for m in misses if m.action == "inline_skip"]
    if not skip_misses:
        return explanations

    # Filter noise
    noise_patterns = ("which which", "has also", "virus have", "virus is",
                      "classifi ", "the the", "a virus", "so generally")
    real_skips = [m for m in skip_misses
                  if not any(n in m.term.lower() for n in noise_patterns)
                  and len(m.term.split()) <= 3
                  and len(m.term) >= 3]

    if not real_skips:
        return explanations

    # Group by source_group
    by_group: dict[str, list[MissReport]] = {}
    for m in real_skips:
        by_group.setdefault(m.source_group, []).append(m)

    for group_name, group_misses in by_group.items():
        # Find the matching explanation
        expl = None
        for e in explanations:
            if e.get("topic_name") == group_name and not e.get("was_skipped"):
                expl = e
                break

        if not expl or not expl.get("explanation_text"):
            continue

        # Build skip-lines block
        skip_lines = []
        for m in group_misses:
            skip_lines.append(f"🟡 **{m.term}** — mentioned in lecture, low priority (CI% {m.ci_percent}%). Expand?")

        skip_block = "\n\n> **Also mentioned in this lecture section:**\n> " + "\n> ".join(skip_lines)

        expl["explanation_text"] = expl["explanation_text"].rstrip() + skip_block
        expl["word_count"] = len(expl["explanation_text"].split())
        print(f"  Inserted {len(group_misses)} inline skip-lines into: {group_name}")

    # Handle slide-sourced misses (content on slides but not in transcript)
    slide_skips = [m for m in real_skips if m.source_group.startswith("Slide:")]
    if slide_skips:
        # Append to the LAST non-skipped explanation
        last_expl = None
        for e in reversed(explanations):
            if not e.get("was_skipped") and e.get("explanation_text"):
                last_expl = e
                break

        if last_expl:
            slide_lines = [m.skip_line for m in slide_skips]
            slide_block = "\n\n> **Also shown on lecture slides:**\n> " + "\n> ".join(slide_lines)
            last_expl["explanation_text"] = last_expl["explanation_text"].rstrip() + slide_block
            last_expl["word_count"] = len(last_expl["explanation_text"].split())
            print(f"  Inserted {len(slide_skips)} slide-term skip-lines at end")

    return explanations


def auto_fix(
    explanations: list[dict],
    groups: list,
    ci_threshold: int = 50,
    screenshots: list[dict] | None = None,
) -> tuple[list[dict], list[MissReport]]:
    """Run completeness check and auto-fix both high and low CI% misses.

    Returns (updated_explanations, miss_report).
    """
    misses = check_completeness(explanations, groups, ci_threshold,
                                screenshots=screenshots)
    if not misses:
        print("Completeness check: all terms covered.")
        return explanations, misses

    print(format_report(misses))

    # Report high-CI% misses (patching disabled — too destructive, fixes should be in the prompt)
    regen = [m for m in misses if m.action == "regeneration_target"]
    if regen:
        print(f"\n{len(regen)} high-CI% terms missing (will be caught by Stage 3 evaluator):"
              f"\n  " + ", ".join(m.term for m in regen))

    # Insert inline skips for low-CI% misses
    skips = [m for m in misses if m.action == "inline_skip"]
    if skips:
        print(f"\nInserting {len(skips)} inline skip-lines...")
        explanations = insert_inline_skips(explanations, misses, groups)

    return explanations, misses
