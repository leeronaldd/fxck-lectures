#!/usr/bin/env python3
"""Stage 2 CLI: Generate tutor-quality explanations from lecture chunks.

V4 Pipeline:
    Stage 1 chunks → CI% scoring → Concept Grouping → Generation → Completeness Check → Slide References

Usage:
    # Full v4 pipeline (recommended)
    python run_stage2.py data/output/final_chunks_v5.json --v4

    # V4 with pre-computed CI scores
    python run_stage2.py data/output/final_chunks_v5.json --v4 --ci data/output/ci_scores.json

    # V4 dry-run (print prompts, no LLM calls for generation)
    python run_stage2.py data/output/final_chunks_v5.json --v4 --dry-run

    # V4 with specific groups only
    python run_stage2.py data/output/final_chunks_v5.json --v4 --groups 2,4,5

    # V4 deterministic grouping (no LLM for grouping step)
    python run_stage2.py data/output/final_chunks_v5.json --v4 --no-llm-group

    # Legacy: chunk-by-chunk generation (original pipeline)
    python run_stage2.py data/output/final_chunks_v5.json --chunks 2,7,8
"""

import argparse
import json
import sys

# Fix Windows console encoding for emoji output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

from src.generator import generate_all, generate_from_slides, generate_from_groups


def run_v4_pipeline(args):
    """Run the full v4 pipeline: CI% → Concept Groups → Generation → Completeness → Slides."""
    from src.models import Chunk, CIScore
    from src.concept_grouper import (
        group_chunks_with_llm, group_chunks_deterministic,
        save_groups, load_groups_with_transcripts,
    )
    from src.completeness_checker import check_completeness, format_report, save_report, auto_fix

    chunks_path = args.chunks_path
    output_dir = Path(args.output).parent if args.output else Path("data/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Step 1: Load chunks ---
    with open(chunks_path, "r", encoding="utf-8") as f:
        raw_chunks = json.load(f)
    chunks = [Chunk(**c) for c in raw_chunks]
    print(f"Loaded {len(chunks)} chunks from {chunks_path}")

    # --- Step 2: CI% Scoring ---
    ci_scores_map: dict[int, CIScore] = {}
    if args.ci:
        with open(args.ci, "r", encoding="utf-8") as f:
            ci_raw = json.load(f)
        for cs in ci_raw:
            ci_scores_map[cs["chunk_index"]] = CIScore(**cs)
        print(f"Loaded {len(ci_scores_map)} CI scores from {args.ci}")
    elif not args.skip_ci:
        print("\n--- Step 1.5a: CI% Scoring ---")
        from src.ci_scorer import score_all
        ci_output = str(output_dir / "v4_ci_scores.json")
        scores = score_all(chunks_path, output_path=ci_output)
        for s in scores:
            ci_scores_map[s.chunk_index] = s
        print(f"Scored {len(scores)} chunks")
    else:
        print("Skipping CI% scoring (--skip-ci)")

    # --- Step 3: Concept Grouping ---
    print("\n--- Step 2: Concept Grouping ---")
    if args.no_llm_group:
        groups = group_chunks_deterministic(chunks, ci_scores_map or None)
        print(f"Deterministic grouping: {len(groups)} groups")
    else:
        groups = group_chunks_with_llm(chunks, ci_scores_map or None)
        print(f"LLM grouping: {len(groups)} groups")

    # Save groups
    groups_output = str(output_dir / "v4_concept_groups.json")
    save_groups(groups, groups_output)

    # Print group summary
    print("\nConcept Groups:")
    for g in groups:
        action_tag = ""
        if g.action == "skip":
            action_tag = f" → SKIP: {g.skip_message}"
        elif g.action == "minimal":
            action_tag = " → MINIMAL"
        elif g.needs_expansion:
            action_tag = " → EXPAND"
        print(f"  {g.group_index}. {g.group_name} (CI% {g.ci_percent}%, chunks {g.chunk_indices}){action_tag}")

    # --- Step 4: Generation ---
    print("\n--- Step 3: Explanation Generation ---")
    group_indices = None
    if args.groups:
        try:
            group_indices = [int(x.strip()) for x in args.groups.split(",")]
            print(f"Processing only groups: {group_indices}")
        except ValueError:
            print(f"Error: --groups must be comma-separated integers, got '{args.groups}'")
            sys.exit(1)

    output_path = args.output or str(output_dir / "v4_explanations.json")
    explanations = generate_from_groups(
        groups=groups,
        output_path=output_path,
        dry_run=args.dry_run,
        group_indices=group_indices,
    )

    if args.dry_run:
        print("\nDry run complete. No LLM calls made for generation.")
        return

    # --- Step 4.5: Fact-Check & Exam Grounding ---
    if explanations and not args.skip_verify:
        print("\n--- Step 4.5: Verify & Ground ---")
        from src.fact_checker import (
            verify_and_ground, format_verification_report, save_verification_report,
        )
        explanation_dicts_for_verify = [e.model_dump() for e in explanations]
        _, verifications = verify_and_ground(explanation_dicts_for_verify, groups)
        print(format_verification_report(verifications))
        if verifications:
            verify_path = str(output_dir / "v4_verification_report.json")
            save_verification_report(verifications, verify_path)

    # --- Step 5: Completeness Check + Auto-Fix ---
    if explanations and not args.skip_completeness:
        print("\n--- Step 4: Completeness Check + Auto-Fix ---")
        explanation_dicts = [e.model_dump() for e in explanations]
        # Load screenshots for slide-term checking if available
        completeness_screenshots = None
        if args.screenshots:
            try:
                with open(args.screenshots, "r", encoding="utf-8") as f:
                    completeness_screenshots = json.load(f)
            except Exception:
                pass

        explanation_dicts, misses = auto_fix(
            explanation_dicts, groups,
            screenshots=completeness_screenshots,
        )

        if misses:
            report_path = str(output_dir / "v4_completeness_report.json")
            save_report(misses, report_path)

        # Write back patched explanations to the Explanation objects
        for expl_obj, expl_dict in zip(explanations, explanation_dicts):
            expl_obj.explanation_text = expl_dict["explanation_text"]
            expl_obj.word_count = expl_dict["word_count"]

        # Re-save patched explanations
        from src.generator import _save_explanations
        _save_explanations(explanations, output_path)

    # --- Step 6: Slide References ---
    # Slides are inserted inline during assembly via keyword matching (zero LLM calls).
    # The old Flash-based slide_inserter.py step (~20 Flash calls, mostly failing) is removed.
    # Companion slides doc still generated if screenshots provided.
    if explanations and args.screenshots and not args.skip_slides:
        from src.slide_inserter import build_companion_slides_doc
        with open(args.screenshots, "r", encoding="utf-8") as f:
            slides = json.load(f)
        companion_path = str(output_dir / "v4_companion_slides.md")
        build_companion_slides_doc(slides, companion_path)

    # --- Step 7: Assemble final markdown ---
    if explanations:
        # Load screenshots for image embedding if available
        assembly_screenshots = None
        if args.screenshots:
            try:
                with open(args.screenshots, "r", encoding="utf-8") as f:
                    assembly_screenshots = json.load(f)
            except Exception:
                pass

        md_path = str(output_dir / "v4_lecture_replacement.md")
        assemble_markdown(explanations, md_path,
                          screenshots=assembly_screenshots, groups=groups)

    # Preview
    if args.preview and explanations:
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"{'Grp':<4} {'Topic':<45} {'Words':<7} {'Status'}")
        print("-" * 70)
        for e in explanations:
            status = ""
            if e.was_skipped:
                status = "SKIPPED"
            elif e.was_expanded:
                status = "EXPANDED"
            print(f"{e.chunk_index:<4} {e.topic_name[:44]:<45} {e.word_count:<7} {status}")
        print("-" * 70)
        total = sum(e.word_count for e in explanations)
        print(f"{'':4} {'TOTAL':<45} {total:<7}")


def _deduplicate_slides(slides: list[dict]) -> list[dict]:
    """Remove near-duplicate slides (same slide captured at different moments).

    Uses Gemini Flash to semantically identify duplicates — catches cases where
    the same slide is described differently (e.g., zoomed in vs zoomed out,
    different frame of the same content). Falls back to word-overlap if Flash fails.

    Works for any lecture — no hardcoded slide indices.
    """
    if len(slides) <= 1:
        return slides

    try:
        from google import genai
        from src.config import GCP_PROJECT_ID, GCP_LOCATION, CHUNKER_FALLBACK_MODEL

        # Build a COMPACT list — short descriptions to keep prompt small
        slide_list = []
        for i, s in enumerate(slides):
            desc = s.get("description", "")[:80].split(".")[0]
            slide_list.append(f"{i}: {desc}")

        prompt = (
            "These are descriptions of lecture slide screenshots. Some may be duplicates "
            "(same slide captured at different moments or zoom levels).\n\n"
            "Return a JSON array of indices to REMOVE (duplicates only). "
            "If slide X and Y show the same content, remove the worse one.\n"
            "If no duplicates, return []\n\n"
            "SLIDES:\n" + "\n".join(slide_list)
        )

        client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)
        response = client.models.generate_content(
            model=CHUNKER_FALLBACK_MODEL,
            contents=prompt,
            config={
                "temperature": 0.1,
                "max_output_tokens": 1024,
            },
        )

        from src.json_repair import extract_json
        remove_indices = set(extract_json(response.text, expect_array=True))
        unique = [s for i, s in enumerate(slides) if i not in remove_indices]

        if len(unique) < len(slides):
            print(f"  Dedup: {len(slides)} slides → {len(unique)} unique")
        return unique if unique else slides

    except Exception as e:
        print(f"  Dedup fallback (Flash failed: {e})")
        # Fallback: simple word-overlap dedup
        import re as _re

        def _sig_words(desc: str) -> set[str]:
            clean = _re.sub(r'\*{1,2}', '', desc.lower())
            return set(w for w in clean.split() if len(w) >= 5
                       and w not in {"this", "these", "those", "which", "lecture",
                                     "slide", "shows", "illustrates", "various"})

        unique = []
        for slide in slides:
            words = _sig_words(slide.get("description", ""))
            is_dup = False
            for i, kept in enumerate(unique):
                kept_words = _sig_words(kept.get("description", ""))
                if not words or not kept_words:
                    continue
                overlap = len(words & kept_words) / min(len(words), len(kept_words))
                if overlap > 0.5:  # lowered threshold for fallback
                    if len(slide.get("description", "")) > len(kept.get("description", "")):
                        unique[i] = slide
                    is_dup = True
                    break
            if not is_dup:
                unique.append(slide)

        if len(unique) < len(slides):
            print(f"  Dedup (fallback): {len(slides)} slides → {len(unique)} unique")
        return unique


def _insert_slides_inline(text: str, slides: list[dict], max_slides: int = 4) -> str:
    """Insert slide images inline at the most relevant paragraph.

    Uses keyword overlap between slide descriptions and paragraph content.
    Zero LLM calls — pure string matching. Cap at max_slides per section.

    Works for any lecture — matches on content, not hardcoded positions.
    """
    import re as _re

    if not slides or not text:
        return text

    # Limit slides per section
    slides = slides[:max_slides]

    # Split text into paragraphs (preserve headers)
    paragraphs = text.split("\n\n")
    if len(paragraphs) <= 1:
        return text

    def _keywords(s: str) -> set[str]:
        """Extract significant words for matching."""
        clean = _re.sub(r'[*#\[\]()]', '', s.lower())
        return set(w for w in clean.split() if len(w) >= 5
                   and w not in {"these", "those", "which", "their", "about",
                                 "where", "would", "could", "should", "there",
                                 "other", "being", "using", "image", "slide",
                                 "lecture", "shows", "illustrates", "various"})

    # For each slide, find the best matching paragraph
    insertions: list[tuple[int, dict]] = []  # (paragraph_index, slide)
    used_paragraphs: set[int] = set()

    for slide in slides:
        desc_words = _keywords(slide.get("description", ""))
        if not desc_words:
            continue

        best_idx = -1
        best_score = 0

        for i, para in enumerate(paragraphs):
            if i in used_paragraphs:
                continue
            # Skip very short paragraphs (headers, single lines)
            if len(para.split()) < 10:
                continue
            para_words = _keywords(para)
            overlap = len(desc_words & para_words)
            if overlap > best_score:
                best_score = overlap
                best_idx = i

        if best_idx >= 0 and best_score >= 2:
            insertions.append((best_idx, slide))
            used_paragraphs.add(best_idx)

    # Insert slides AFTER their matching paragraph (reverse order to preserve indices)
    for para_idx, slide in sorted(insertions, key=lambda x: -x[0]):
        img = slide.get("image_filename", slide.get("slide_image", ""))
        caption = _clean_slide_caption(slide.get("description", ""))
        slide_md = f"\n![{caption}](screenshots/{img})\n*{caption}*"
        paragraphs[para_idx] = paragraphs[para_idx] + slide_md

    return "\n\n".join(paragraphs)


def _clean_slide_caption(description: str) -> str:
    """Clean a slide description into a readable caption.

    Removes markdown artifacts, truncates at sentence boundary, keeps it short.
    """
    import re as _re
    if not description:
        return "Lecture slide"
    # Strip markdown bold/italic artifacts
    caption = _re.sub(r'\*{1,2}', '', description)
    # Take first sentence only
    first_sentence = caption.split(".")[0].strip()
    # Cap at 120 chars, break at word boundary
    if len(first_sentence) > 120:
        first_sentence = first_sentence[:117].rsplit(" ", 1)[0] + "..."
    return first_sentence if first_sentence else "Lecture slide"


def assemble_markdown(explanations: list, output_path: str,
                      screenshots: list[dict] | None = None,
                      groups: list | None = None):
    """Assemble explanations into a single readable markdown document.

    Automatically adds:
    - Skip emoji on skipped sections
    - Inline slide images matched to paragraphs
    - Emojis are generated by Gemini Pro on ### sub-headings (not added by assembly)
    """

    # Build screenshot lookup: group_index -> list of slides
    # Strategy: for each slide, find the BEST matching group (not first above threshold)
    # Uses both timestamp-based chunk mapping AND content-based description matching
    slide_map: dict[int, list[dict]] = {}
    if screenshots and groups:
        # Filter out blank/black slides
        valid_slides = [
            s for s in screenshots
            if s.get("description", "").strip()
            and "black screen" not in s.get("description", "").lower()
            and "no visible" not in s.get("description", "").lower()
        ]

        # Deduplicate near-identical slides (same slide captured at different moments)
        # Two slides are "duplicates" if their descriptions share >70% of significant words
        valid_slides = _deduplicate_slides(valid_slides)

        # Pre-compute group text for each non-skipped group (topic name + key terms only,
        # NOT the full explanation — that's too greedy and big groups vacuum up everything)
        group_texts: dict[int, str] = {}
        for group in groups:
            if group.action == "skip":
                continue
            text_parts = [group.group_name.lower()]
            text_parts.extend(t.lower() for t in group.key_terms)
            # Add expansion hints (they contain topic-specific keywords)
            text_parts.extend(h.lower() for h in group.expansion_hints)
            group_texts[group.group_index] = " ".join(text_parts)

        # For each slide, score against ALL groups and assign to the best one
        for s in valid_slides:
            desc = s.get("description", "").lower()
            desc_words = set(w for w in desc.split() if len(w) > 4)

            best_group = -1
            best_score = 0

            for group in groups:
                if group.group_index not in group_texts:
                    continue

                score = 0

                # Timestamp-based chunk mapping (original signal)
                if s.get("matched_chunk_index") in group.chunk_indices:
                    score += 3

                # Content-based: key terms from slide description in group topic/terms
                group_text = group_texts[group.group_index]
                for word in desc_words:
                    if word in group_text:
                        score += 1

                if score > best_score:
                    best_score = score
                    best_group = group.group_index

            if best_group >= 0 and best_score >= 2:
                slide_map.setdefault(best_group, []).append(s)

    lines = ["# 📖 Lecture Replacement\n"]
    lines.append("*Generated by your personal AI tutor — read this instead of watching the lecture.*\n")
    lines.append("---\n")

    # Detect overview/minimal sections by checking the explanation object, not topic name
    for expl in explanations:
        if expl.was_skipped:
            lines.append(f"⏭️ {expl.explanation_text}")
            lines.append("")
        elif expl.word_count < 50:
            lines.append(f"## {expl.topic_name}\n")
            lines.append(expl.explanation_text)
            lines.append("\n---\n")
        else:
            lines.append(f"## {expl.topic_name}\n")

            # Insert slides INLINE at their best-matching paragraph (not as a dump)
            group_idx = expl.chunk_index
            section_slides = slide_map.get(group_idx, [])

            # Insert slides into the explanation text at the most relevant paragraph
            text_with_slides = _insert_slides_inline(
                expl.explanation_text, section_slides
            )
            lines.append(text_with_slides)

            lines.append("\n---\n")

    # Append unassigned slides as a reference section
    if screenshots and groups:
        all_assigned = set()
        for slides_list in slide_map.values():
            for s in slides_list:
                all_assigned.add(s.get("image_filename", ""))

        unassigned = [
            s for s in screenshots
            if s.get("image_filename", "") not in all_assigned
            and s.get("description", "").strip()
            and "black screen" not in s.get("description", "").lower()
            and "no visible" not in s.get("description", "").lower()
        ]
        if unassigned:
            lines.append("\n## 📎 Additional Lecture Slides\n")
            lines.append("*These slides were shown during the lecture but didn't map to a specific section above.*\n")
            for s in unassigned:
                img = s.get("image_filename", "")
                caption = _clean_slide_caption(s.get("description", ""))
                lines.append(f"![{caption}](screenshots/{img})")
                lines.append(f"*{caption}*\n")

    md_text = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_text)

    # Report slide distribution
    if screenshots:
        total_slides = len([s for s in screenshots
                           if "black screen" not in s.get("description", "").lower()])
        assigned_count = sum(len(v) for v in slide_map.values())
        print(f"\nAssembled lecture replacement: {output_path}")
        print(f"  Total: {len(md_text):,} chars, ~{len(md_text.split()):,} words")
        print(f"  Slides: {assigned_count} assigned to sections, "
              f"{total_slides - assigned_count} in appendix, {total_slides} total")
    else:
        print(f"\nAssembled lecture replacement: {output_path}")
        print(f"  Total: {len(md_text):,} chars, ~{len(md_text.split()):,} words")


def main():
    parser = argparse.ArgumentParser(
        description="Stage 2: Generate tutor-quality explanations from lecture chunks"
    )
    parser.add_argument(
        "chunks_path",
        help="Path to Stage 1 chunks JSON (e.g., data/output/final_chunks_v5.json)",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output path for explanations JSON (auto-generated if omitted)",
    )

    # V4 pipeline flags
    parser.add_argument(
        "--v4", action="store_true",
        help="Use v4 pipeline: concept grouping → generation → completeness → slides",
    )
    parser.add_argument(
        "--groups",
        help="Comma-separated group indices to process (v4 only, e.g., 2,4,5)",
    )
    parser.add_argument(
        "--no-llm-group", action="store_true",
        help="Use deterministic concept grouping instead of LLM (v4 only)",
    )
    parser.add_argument(
        "--skip-ci", action="store_true",
        help="Skip CI% scoring step (v4 only)",
    )
    parser.add_argument(
        "--skip-completeness", action="store_true",
        help="Skip completeness check (v4 only)",
    )
    parser.add_argument(
        "--skip-verify", action="store_true",
        help="Skip fact-check and exam grounding (v4 only)",
    )
    parser.add_argument(
        "--skip-slides", action="store_true",
        help="Skip slide reference insertion (v4 only)",
    )

    # Common flags
    parser.add_argument(
        "--ci",
        help="Path to pre-computed CI scores JSON",
    )
    parser.add_argument(
        "--screenshots",
        help="Path to screenshots JSON (for slide references)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print prompts without making LLM calls",
    )
    parser.add_argument(
        "-p", "--preview", action="store_true",
        help="Print a summary table after generation",
    )

    # Legacy flags
    parser.add_argument(
        "-c", "--chunks",
        help="Legacy: comma-separated chunk indices (non-v4 mode)",
    )
    parser.add_argument(
        "--slide-chunks",
        help="Legacy: path to slide chunks JSON for slide-based mode",
    )

    args = parser.parse_args()

    if args.v4:
        run_v4_pipeline(args)
    elif args.slide_chunks:
        # Legacy slide-based mode
        generate_from_slides(
            slide_chunks_path=args.slide_chunks,
            output_path=args.output,
            ci_scores_path=args.ci,
            dry_run=args.dry_run,
        )
    else:
        # Legacy chunk-by-chunk mode
        chunk_indices = None
        if args.chunks:
            try:
                chunk_indices = [int(x.strip()) for x in args.chunks.split(",")]
            except ValueError:
                print(f"Error: --chunks must be comma-separated integers, got '{args.chunks}'")
                sys.exit(1)

        explanations = generate_all(
            chunks_path=args.chunks_path,
            output_path=args.output,
            chunk_indices=chunk_indices,
            dry_run=args.dry_run,
            ci_scores_path=args.ci,
            screenshots_path=args.screenshots,
        )

        if args.preview and explanations:
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"{'Idx':<4} {'Topic':<45} {'Words':<7} {'Status'}")
            print("-" * 70)
            for e in explanations:
                status = ""
                if e.was_skipped:
                    status = "SKIPPED"
                elif e.was_expanded:
                    status = "EXPANDED"
                print(f"{e.chunk_index:<4} {e.topic_name[:44]:<45} {e.word_count:<7} {status}")
            print("-" * 70)
            total = sum(e.word_count for e in explanations)
            print(f"{'':4} {'TOTAL':<45} {total:<7}")


if __name__ == "__main__":
    main()
