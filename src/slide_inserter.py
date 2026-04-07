"""Slide Reference Inserter: post-processing step that maps slides to text.

Uses Gemini Flash to find the best paragraph for each slide reference,
then inserts *(See Slide N)* naturally into the text.
"""

import json
import re

from src.config import GCP_PROJECT_ID, GCP_LOCATION, CHUNKER_FALLBACK_MODEL


MAPPING_PROMPT = """Given this explanation text and a slide description, identify which paragraph the slide best corresponds to.

SLIDE {slide_index}: {slide_description}

EXPLANATION TEXT (paragraphs numbered):
{numbered_paragraphs}

Return ONLY a JSON object:
{{"paragraph_number": 3, "insert_after_sentence": "The specific sentence after which to insert the slide reference."}}

If the slide doesn't match any paragraph well, return:
{{"paragraph_number": -1, "insert_after_sentence": ""}}"""


def insert_slide_references(
    explanation_text: str,
    slides: list[dict],
    use_llm: bool = True,
) -> str:
    """Insert *(See Slide N)* references into explanation text.

    Args:
        explanation_text: the generated explanation markdown
        slides: list of slide dicts with slide_index and slide_description
        use_llm: if True, use Flash to find best placement; if False, skip

    Returns:
        Updated explanation text with slide references inserted.
    """
    if not slides or not use_llm:
        return explanation_text

    from google import genai

    client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)

    # Split into paragraphs
    paragraphs = [p.strip() for p in explanation_text.split("\n\n") if p.strip()]
    numbered = "\n\n".join(
        f"[{i+1}] {p}" for i, p in enumerate(paragraphs)
    )

    insertions = []  # (paragraph_index, sentence, slide_index)

    for slide in slides:
        prompt = MAPPING_PROMPT.format(
            slide_index=slide.get("slide_index", "?"),
            slide_description=slide.get("description", slide.get("slide_description", "")),
            numbered_paragraphs=numbered,
        )

        try:
            response = client.models.generate_content(
                model=CHUNKER_FALLBACK_MODEL,
                contents=prompt,
                config={"temperature": 0.1, "max_output_tokens": 256},
            )
            from src.json_repair import extract_json
            result = extract_json(response.text, expect_array=False)
            para_num = result.get("paragraph_number", -1)
            sentence = result.get("insert_after_sentence", "")

            if para_num > 0 and sentence:
                insertions.append((para_num - 1, sentence, slide.get("slide_index", "?")))
        except Exception as e:
            print(f"  Warning: Slide {slide.get('slide_index', '?')} mapping failed: {e}")
            continue

    # Apply insertions (reverse order to preserve indices)
    for para_idx, sentence, slide_idx in sorted(insertions, key=lambda x: -x[0]):
        if 0 <= para_idx < len(paragraphs):
            ref = f" *(See Slide {slide_idx})*"
            # Try to insert after the matching sentence
            if sentence and sentence in paragraphs[para_idx]:
                paragraphs[para_idx] = paragraphs[para_idx].replace(
                    sentence, sentence + ref, 1
                )
            else:
                # Fallback: append to end of paragraph
                paragraphs[para_idx] = paragraphs[para_idx].rstrip() + ref

    return "\n\n".join(paragraphs)


def build_companion_slides_doc(
    slides: list[dict],
    output_path: str | None = None,
) -> str:
    """Generate a companion slides reference document.

    Args:
        slides: list of slide dicts with index, description, image filename
        output_path: if provided, save to this path

    Returns:
        Markdown string of the companion slides document.
    """
    lines = ["# Companion Slides Reference\n"]
    lines.append("*Use alongside the lecture replacement document.*\n")

    for slide in sorted(slides, key=lambda s: s.get("slide_index", 0)):
        idx = slide.get("slide_index", "?")
        desc = slide.get("description", slide.get("slide_description", "No description"))
        img = slide.get("image_filename", slide.get("slide_image", ""))

        lines.append(f"## Slide {idx}")
        if img:
            lines.append(f"![Slide {idx}](screenshots/{img})")
        lines.append(f"{desc}\n")

    doc = "\n".join(lines)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(doc)
        print(f"Saved companion slides to {output_path}")

    return doc
