"""Concept Grouper: merges, reorders, and marks skips on Stage 1 chunks.

Takes 14 regex chunks and produces ~5-7 logical concept groups for Stage 2.
Uses Gemini Flash for intelligent grouping decisions.
"""

import json
from dataclasses import dataclass, field, asdict

from src.models import Chunk, CIScore
from src.config import GCP_PROJECT_ID, GCP_LOCATION, CHUNKER_FALLBACK_MODEL


@dataclass
class ConceptGroup:
    group_index: int
    group_name: str                          # e.g., "Enzyme Kinetics" or "Viral Replication"
    chunk_indices: list[int]                 # which Stage 1 chunks are merged here
    action: str                              # "generate", "skip", "minimal"
    ci_percent: int = 50                     # aggregated CI% (max of constituent chunks)
    skip_message: str = ""                   # one-liner for skipped groups
    raw_transcript: str = ""                 # full transcript text (stored for expand-on-demand)
    key_terms: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    expansion_hints: list[str] = field(default_factory=list)
    needs_expansion: bool = False
    emphasis_score: str = "MEDIUM"


# ---------------------------------------------------------------------------
# Grouping prompt for Gemini Flash
# ---------------------------------------------------------------------------

GROUPING_PROMPT = """You are organizing a lecture transcript into logical concept groups for a personal tutor to explain.

The professor's ordering was chaotic. Your job is to:
1. MERGE related chunks into logical groups (e.g., merge "Overview of Topic X" + "Subtypes of Topic X" into one group)
2. REORDER if the professor's sequence was illogical for learning
3. MARK SKIPS for content a tutor would skip (housekeeping, yap, tangential history)

Here are the chunks from Stage 1:

{chunks_summary}

CI% scores (exam importance, 0-100):
{ci_summary}

Return ONLY a JSON array of concept groups. Each group:
{{
  "group_name": "Human-readable topic name",
  "chunk_indices": [2, 3],
  "action": "generate" | "skip" | "minimal",
  "skip_message": "Only if action=skip. One line like: Professor rambled about naming history. Not tested.",
  "needs_expansion": true/false,
  "expansion_hints": ["Brief hint about what to expand"]
}}

Rules:
- Housekeeping/admin chunks (typically the first 1-2 chunks) → action "minimal" or "skip"
- Low CI% yap content → action "skip" with a snarky one-liner
- Related chunks should be merged (don't create 14 groups from 14 chunks)
- Target 5-8 groups total
- Order groups for optimal learning flow (foundations before advanced)
- If two chunks cover the same framework (e.g., overview + detail), merge into ONE group
- If professor skimmed something important (needs_expansion=true in source), flag it
- Add expansion_hints for complex topics: how to group sub-concepts, what to explain first, what's hardest"""


def _build_chunks_summary(chunks: list[Chunk]) -> str:
    """Build a compact summary of chunks for the grouping prompt."""
    lines = []
    for c in chunks:
        expansion = " [NEEDS EXPANSION]" if c.needs_expansion else ""
        terms = ", ".join(c.key_terms[:8]) if c.key_terms else "none"
        lines.append(
            f"Chunk {c.chunk_index}: \"{c.topic_name}\" "
            f"({c.word_count} words, emphasis={c.emphasis_score}{expansion})\n"
            f"  Key terms: {terms}\n"
            f"  First 100 chars: \"{c.transcript_text[:100].strip()}...\""
        )
    return "\n\n".join(lines)


def _build_ci_summary(ci_scores: dict[int, CIScore]) -> str:
    """Build CI% summary string."""
    if not ci_scores:
        return "No CI% scores available. Use your best judgment."
    lines = []
    for idx in sorted(ci_scores.keys()):
        cs = ci_scores[idx]
        lines.append(f"Chunk {idx}: {cs.ci_percent}% — {cs.ci_reasoning[:80]}")
    return "\n".join(lines)


def group_chunks_with_llm(
    chunks: list[Chunk],
    ci_scores: dict[int, CIScore] | None = None,
) -> list[ConceptGroup]:
    """Use Gemini Flash to intelligently group chunks."""
    from google import genai

    ci_map = ci_scores or {}
    prompt = GROUPING_PROMPT.format(
        chunks_summary=_build_chunks_summary(chunks),
        ci_summary=_build_ci_summary(ci_map),
    )

    client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)
    response = client.models.generate_content(
        model=CHUNKER_FALLBACK_MODEL,
        contents=prompt,
        config={"temperature": 0.3, "max_output_tokens": 4096},
    )

    from src.json_repair import extract_json
    raw_groups = extract_json(response.text, expect_array=True)

    # Build chunk lookup
    chunk_map = {c.chunk_index: c for c in chunks}

    groups = []
    for i, rg in enumerate(raw_groups):
        indices = rg["chunk_indices"]

        # Aggregate metadata from constituent chunks
        group_chunks = [chunk_map[idx] for idx in indices if idx in chunk_map]
        all_terms = []
        all_prereqs = []
        all_transcripts = []
        max_ci = 0
        max_emphasis = "LOW"
        any_expansion = rg.get("needs_expansion", False)

        for gc in group_chunks:
            all_terms.extend(gc.key_terms)
            all_prereqs.extend(gc.prerequisites)
            all_transcripts.append(gc.transcript_text)
            if gc.needs_expansion:
                any_expansion = True

            # CI%
            if gc.chunk_index in ci_map:
                max_ci = max(max_ci, ci_map[gc.chunk_index].ci_percent)

            # Emphasis (HIGH > MEDIUM > LOW)
            rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
            if rank.get(gc.emphasis_score, 0) > rank.get(max_emphasis, 0):
                max_emphasis = gc.emphasis_score

        # Deduplicate terms
        seen = set()
        unique_terms = []
        for t in all_terms:
            if t.lower() not in seen:
                seen.add(t.lower())
                unique_terms.append(t)

        groups.append(ConceptGroup(
            group_index=i,
            group_name=rg["group_name"],
            chunk_indices=indices,
            action=rg.get("action", "generate"),
            ci_percent=max_ci if ci_map else 50,
            skip_message=rg.get("skip_message", ""),
            raw_transcript="\n\n---\n\n".join(all_transcripts),
            key_terms=unique_terms[:20],
            prerequisites=list(set(all_prereqs))[:10],
            expansion_hints=rg.get("expansion_hints", []),
            needs_expansion=any_expansion,
            emphasis_score=max_emphasis,
        ))

    return groups


def _jaccard(a: set, b: set) -> float:
    """Jaccard similarity between two sets."""
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def _derive_group_name(chunks: list[Chunk]) -> str:
    """Derive a group name from the most common key terms across chunks."""
    from collections import Counter
    term_counts = Counter()
    for c in chunks:
        for t in c.key_terms[:5]:
            term_counts[t.lower()] = term_counts.get(t.lower(), 0) + 1

    if term_counts:
        # Use the top 2 terms as the group name
        top = [t.title() for t, _ in term_counts.most_common(2)]
        return " & ".join(top)
    # Fallback: use the first chunk's topic name
    return chunks[0].topic_name if chunks else "Unknown Topic"


def group_chunks_deterministic(
    chunks: list[Chunk],
    ci_scores: dict[int, CIScore] | None = None,
) -> list[ConceptGroup]:
    """Fallback: deterministic grouping without LLM.

    Groups chunks by key_terms overlap — works for any medical subject.
    First 1-2 chunks become "Course Overview" (minimal), remaining chunks
    are grouped by term similarity.
    """
    ci_map = ci_scores or {}

    if not chunks:
        return []

    # Separate intro chunks from content chunks
    intro_chunks = [c for c in chunks if c.chunk_index <= 1]
    content_chunks = [c for c in chunks if c.chunk_index > 1]

    groups = []
    group_idx = 0

    # First group: Course Overview (minimal)
    if intro_chunks:
        all_terms = []
        all_transcripts = []
        for c in intro_chunks:
            all_terms.extend(c.key_terms)
            all_transcripts.append(c.transcript_text)

        groups.append(ConceptGroup(
            group_index=group_idx,
            group_name="Course Overview",
            chunk_indices=[c.chunk_index for c in intro_chunks],
            action="minimal",
            ci_percent=0,
            raw_transcript="\n\n---\n\n".join(all_transcripts),
            key_terms=list(dict.fromkeys(t.lower() for t in all_terms))[:10],
        ))
        group_idx += 1

    # Group remaining chunks by key_terms similarity
    # Each chunk starts as ungrouped; merge chunks with overlapping terms
    assigned = set()
    cluster_list = []  # list of lists of Chunk

    for chunk in content_chunks:
        if chunk.chunk_index in assigned:
            continue

        cluster = [chunk]
        assigned.add(chunk.chunk_index)
        chunk_terms = set(t.lower() for t in chunk.key_terms)

        # Try to merge subsequent chunks with similar terms
        for other in content_chunks:
            if other.chunk_index in assigned:
                continue
            other_terms = set(t.lower() for t in other.key_terms)
            if _jaccard(chunk_terms, other_terms) >= 0.15:
                cluster.append(other)
                assigned.add(other.chunk_index)
                chunk_terms |= other_terms  # expand the cluster's term set

        cluster_list.append(cluster)

    # Build ConceptGroups from clusters
    for cluster in cluster_list:
        indices = [c.chunk_index for c in cluster]
        all_terms = []
        all_prereqs = []
        all_transcripts = []
        max_ci = 0
        max_emphasis = "LOW"
        any_expansion = False

        for gc in cluster:
            all_terms.extend(gc.key_terms)
            all_prereqs.extend(gc.prerequisites)
            all_transcripts.append(gc.transcript_text)
            if gc.needs_expansion:
                any_expansion = True
            if gc.chunk_index in ci_map:
                max_ci = max(max_ci, ci_map[gc.chunk_index].ci_percent)
            rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
            if rank.get(gc.emphasis_score, 0) > rank.get(max_emphasis, 0):
                max_emphasis = gc.emphasis_score

        # Determine action based on CI%
        if ci_map and max_ci < 20:
            action = "skip"
            skip_msg = f"Low exam relevance (CI% {max_ci}%). Skipped."
        else:
            action = "generate"
            skip_msg = ""

        seen = set()
        unique_terms = []
        for t in all_terms:
            if t.lower() not in seen:
                seen.add(t.lower())
                unique_terms.append(t)

        groups.append(ConceptGroup(
            group_index=group_idx,
            group_name=_derive_group_name(cluster),
            chunk_indices=indices,
            action=action,
            ci_percent=max_ci if ci_map else 50,
            skip_message=skip_msg,
            raw_transcript="\n\n---\n\n".join(all_transcripts),
            key_terms=unique_terms[:20],
            prerequisites=list(set(all_prereqs))[:10],
            needs_expansion=any_expansion,
            emphasis_score=max_emphasis,
        ))
        group_idx += 1

    return groups


def save_groups(groups: list[ConceptGroup], output_path: str):
    """Save concept groups to JSON."""
    data = [asdict(g) for g in groups]
    # Don't save raw_transcript in the main output (too large)
    # Store it separately
    for d in data:
        d["raw_transcript_length"] = len(d["raw_transcript"])
        del d["raw_transcript"]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(groups)} concept groups to {output_path}")


def load_groups_with_transcripts(
    groups_path: str, chunks_path: str
) -> list[ConceptGroup]:
    """Load concept groups and reattach transcript text from chunks."""
    with open(groups_path, "r", encoding="utf-8") as f:
        raw_groups = json.load(f)
    with open(chunks_path, "r", encoding="utf-8") as f:
        raw_chunks = json.load(f)

    chunk_map = {c["chunk_index"]: c["transcript_text"] for c in raw_chunks}

    groups = []
    for rg in raw_groups:
        indices = rg["chunk_indices"]
        transcript = "\n\n---\n\n".join(
            chunk_map.get(idx, "") for idx in indices
        )
        groups.append(ConceptGroup(
            group_index=rg["group_index"],
            group_name=rg["group_name"],
            chunk_indices=indices,
            action=rg["action"],
            ci_percent=rg.get("ci_percent", 50),
            skip_message=rg.get("skip_message", ""),
            raw_transcript=transcript,
            key_terms=rg.get("key_terms", []),
            prerequisites=rg.get("prerequisites", []),
            expansion_hints=rg.get("expansion_hints", []),
            needs_expansion=rg.get("needs_expansion", False),
            emphasis_score=rg.get("emphasis_score", "MEDIUM"),
        ))

    return groups
