"""Stage 1.5a: CI% (Curriculum Importance) Scorer.

Scores each chunk 0-100 on how likely it is to be assessed on exams.
Uses Gemini Flash via Vertex AI — this is a cheap, fast scoring task.

CI% uses BOTH professor emphasis signals AND external medical curriculum
knowledge. The professor is unreliable, so curriculum standards take priority.
"""

import json
import time

from src.models import Chunk, CIScore, SlideChunk
from src.config import GCP_PROJECT_ID, GCP_LOCATION, CHUNKER_FALLBACK_MODEL


# ---------------------------------------------------------------------------
# Housekeeping detection — skip LLM for non-teaching chunks
# ---------------------------------------------------------------------------

HOUSEKEEPING_KEYWORDS = [
    "housekeeping", "introduction", "course overview", "welcome",
    "office hours", "contact", "assessment", "grading", "syllabus",
    "attendance", "announcements", "admin",
]


def _is_housekeeping(chunk: Chunk) -> bool:
    """Check if a chunk is housekeeping/admin content (CI% = 0)."""
    name_lower = chunk.topic_name.lower()
    for keyword in HOUSEKEEPING_KEYWORDS:
        if keyword in name_lower:
            return True
    # Check transcript content for housekeeping signals (not chunk index — that's brittle)
    if chunk.word_count < 100 and chunk.emphasis_score == "LOW":
        return True
    return False


def _depth_recommendation(ci_percent: int) -> str:
    """Map CI% to a depth recommendation for Stage 2."""
    if ci_percent >= 70:
        return "deep"
    elif ci_percent >= 40:
        return "standard"
    else:
        return "light"


# ---------------------------------------------------------------------------
# LLM scoring
# ---------------------------------------------------------------------------

CI_PROMPT_TEMPLATE = """You are an expert medical curriculum advisor scoring topics for exam importance.

TASK: Estimate how likely this topic is to appear on a 1st-year Biomedical Science exam (0-100%).

TOPIC: {topic_name}
KEY TERMS: {key_terms}
PROFESSOR EMPHASIS: {emphasis_score}
EMPHASIS SIGNALS: {emphasis_signals}
TRANSCRIPT EXCERPT: \"\"\"{transcript_excerpt}\"\"\"

CRITICAL: The professor is unreliable. He skims complex assessable topics and YAPS on easy ones. He says contradictory things. Base your CI% PRIMARILY on what medical school curricula typically assess, NOT on professor emphasis.

USE THE FULL 0-100 RANGE. Be bold. A real tutor takes risks on what to skip.

Scoring guide:
- 85-100: Core concept tested every year. Student MUST know this. (e.g., fundamental mechanisms, classification systems, key pathways)
- 60-84: Important framework, frequently assessed. (e.g., structural components, functional processes, major comparisons)
- 30-59: Supporting knowledge, may appear in context questions. (e.g., specific family/species names, taxonomy details)
- 10-29: Tangential — professor yapped about this but rarely directly tested. (e.g., history of discovery, naming conventions, theoretical origins)
- 0-9: Pure yap or admin. Not assessable. (e.g., housekeeping, anecdotes, "fun facts")

IMPORTANT: Scoring everything 70-90 is USELESS. Differentiate aggressively. Historical trivia and naming conventions should score 10-15. Core mechanisms and classification frameworks should score 85+. If you're unsure, look at the actual content — does it teach HOW something works, or just trivia ABOUT it?

Return ONLY a JSON object (no other text):
{{"ci_percent": 85, "ci_reasoning": "One or two sentences explaining why."}}"""


def score_chunk(chunk: Chunk) -> CIScore:
    """Score a single chunk for curriculum importance.

    Housekeeping chunks get CI% = 0 without an LLM call.
    Teaching chunks are scored by Gemini Flash.
    """
    # Skip LLM for housekeeping
    if _is_housekeeping(chunk):
        return CIScore(
            chunk_index=chunk.chunk_index,
            topic_name=chunk.topic_name,
            ci_percent=0,
            ci_reasoning="Housekeeping/admin content — not assessable.",
            depth_recommendation="light",
            professor_emphasis=chunk.emphasis_score,
        )

    # Build emphasis signals string
    signals_str = ""
    if chunk.emphasis_signals:
        signals_str = "; ".join(
            f'"{s.keyword}" ({s.sentiment})' for s in chunk.emphasis_signals[:5]
        )
    else:
        signals_str = "None detected"

    # Build prompt with truncated transcript (save tokens)
    prompt = CI_PROMPT_TEMPLATE.format(
        topic_name=chunk.topic_name,
        key_terms=", ".join(chunk.key_terms[:10]) if chunk.key_terms else "None",
        emphasis_score=chunk.emphasis_score,
        emphasis_signals=signals_str,
        transcript_excerpt=chunk.transcript_text[:500],
    )

    try:
        from google import genai

        client = genai.Client(
            vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION
        )
        response = client.models.generate_content(
            model=CHUNKER_FALLBACK_MODEL, contents=prompt
        )
        from src.json_repair import extract_json
        result = extract_json(response.text, expect_array=False)

        ci_percent = max(0, min(100, int(result.get("ci_percent", 50))))
        ci_reasoning = result.get("ci_reasoning", "No reasoning provided.")

        return CIScore(
            chunk_index=chunk.chunk_index,
            topic_name=chunk.topic_name,
            ci_percent=ci_percent,
            ci_reasoning=ci_reasoning,
            depth_recommendation=_depth_recommendation(ci_percent),
            professor_emphasis=chunk.emphasis_score,
        )

    except Exception as e:
        print(f"WARNING: CI% scoring failed for chunk {chunk.chunk_index}: {e}")
        # Fallback: use emphasis as a rough proxy
        fallback_ci = {"HIGH": 65, "MEDIUM": 50, "LOW": 30}
        ci = fallback_ci.get(chunk.emphasis_score, 50)
        return CIScore(
            chunk_index=chunk.chunk_index,
            topic_name=chunk.topic_name,
            ci_percent=ci,
            ci_reasoning=f"LLM scoring failed — fallback based on professor emphasis ({chunk.emphasis_score}).",
            depth_recommendation=_depth_recommendation(ci),
            professor_emphasis=chunk.emphasis_score,
        )


def score_all(chunks_path: str, output_path: str | None = None) -> list[CIScore]:
    """Score all chunks from a JSON file.

    Args:
        chunks_path: Path to the Stage 1 chunks JSON file.
        output_path: Where to save CI scores JSON. None = don't save.

    Returns:
        List of CIScore objects.
    """
    with open(chunks_path, "r", encoding="utf-8") as f:
        raw_chunks = json.load(f)

    chunks = [Chunk(**c) for c in raw_chunks]

    # Parallelize CI scoring — each chunk is independent
    from concurrent.futures import ThreadPoolExecutor, as_completed
    scores_map: dict[int, CIScore] = {}
    with ThreadPoolExecutor(max_workers=min(4, len(chunks))) as executor:
        futures = {executor.submit(score_chunk, chunk): chunk.chunk_index for chunk in chunks}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                scores_map[idx] = future.result()
            except Exception as e:
                print(f"WARNING: CI% scoring failed for chunk {idx}: {e}")

    # Preserve original order
    scores: list[CIScore] = [scores_map[c.chunk_index] for c in chunks if c.chunk_index in scores_map]

    if output_path:
        import os
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                [s.model_dump() for s in scores],
                f,
                indent=2,
                ensure_ascii=False,
            )
        print(f"Saved CI scores to: {output_path}")

    return scores


def score_slide(slide: SlideChunk) -> CIScore:
    """Score a single slide chunk for curriculum importance."""
    # Convert slide to duck-type compatible with score_chunk
    # by creating a minimal Chunk-like object
    fake_chunk = Chunk(
        chunk_index=slide.slide_index,
        topic_name=slide.topic_name,
        transcript_text=slide.transcript_text,
        word_count=slide.word_count,
        emphasis_score=slide.emphasis_score,
        emphasis_signals=slide.emphasis_signals,
        key_terms=slide.key_terms,
        prerequisites=[],
        forward_references=[],
    )
    return score_chunk(fake_chunk)


def score_all_slides(slides_path: str, output_path: str | None = None) -> list[CIScore]:
    """Score all slide chunks from a JSON file."""
    with open(slides_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    slides = [SlideChunk(**s) for s in raw]
    scores: list[CIScore] = []

    for slide in slides:
        # Skip very short slides (< 50 words — likely navigation artifacts)
        if slide.word_count < 50:
            scores.append(CIScore(
                chunk_index=slide.slide_index,
                topic_name=slide.topic_name,
                ci_percent=0,
                ci_reasoning="Very short slide — likely transition or navigation.",
                depth_recommendation="light",
                professor_emphasis=slide.emphasis_score,
            ))
            continue

        score = score_slide(slide)
        scores.append(score)
        time.sleep(0.5)

    if output_path:
        import os
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([s.model_dump() for s in scores], f, indent=2, ensure_ascii=False)
        print(f"Saved slide CI scores to: {output_path}")

    return scores
