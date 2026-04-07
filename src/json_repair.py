"""Robust JSON extraction from LLM responses.

Gemini Flash frequently returns truncated JSON — valid up to a cut-off point
but missing closing brackets, quotes, or braces. This module repairs those
responses so the pipeline doesn't fail.

Used across: fact_checker, completeness_checker, slide_inserter, concept_grouper,
chunker, and anywhere Flash returns JSON.
"""

import json
import re


def extract_json(text: str | None, expect_array: bool = True):
    """Extract and repair JSON from an LLM response.

    Handles:
    - Code blocks (```json ... ```)
    - Truncated arrays ([1, 2, 3  ← missing ])
    - Truncated objects ({"key": "val  ← missing "})
    - None/empty responses
    - Leading/trailing garbage text

    Args:
        text: Raw LLM response text
        expect_array: If True, expects a JSON array. If False, expects an object.

    Returns:
        Parsed JSON (list or dict), or empty list/dict on failure.
    """
    if not text or not text.strip():
        return [] if expect_array else {}

    text = text.strip()

    # Step 1: Extract from code blocks
    if "```" in text:
        blocks = text.split("```")
        for block in blocks[1:]:
            cleaned = block.strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
            if cleaned.startswith("[") or cleaned.startswith("{"):
                text = cleaned
                break

    # Step 2: Find the JSON start
    start_char = "[" if expect_array else "{"
    start_idx = text.find(start_char)
    if start_idx == -1:
        return [] if expect_array else {}
    text = text[start_idx:]

    # Step 3: Try parsing as-is
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Step 4: Repair truncated JSON
    repaired = _repair_truncated(text)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # Step 5: Aggressive repair — extract whatever complete items we can
    if expect_array:
        items = _extract_complete_items(text)
        if items:
            return items

    return [] if expect_array else {}


def _repair_truncated(text: str) -> str:
    """Attempt to close truncated JSON by balancing brackets and quotes."""
    # Remove trailing comma (common truncation point)
    text = text.rstrip().rstrip(",")

    # Close any open strings
    # Count unescaped quotes
    in_string = False
    escaped = False
    for char in text:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string

    if in_string:
        text += '"'

    # Close any open objects/arrays — count brackets
    open_braces = text.count("{") - text.count("}")
    open_brackets = text.count("[") - text.count("]")

    # Close incomplete key-value pairs in objects
    # If we ended mid-object after a key, add a null value
    if text.rstrip().endswith(":"):
        text += ' null'
    elif text.rstrip().endswith('":'):
        text += ' null'

    # Add missing closing braces/brackets
    text += "}" * max(0, open_braces)
    text += "]" * max(0, open_brackets)

    return text


def _extract_complete_items(text: str) -> list:
    """Extract whatever complete JSON objects we can from a truncated array.

    For a response like:
    [{"claim": "foo", "type": "bar"}, {"claim": "baz", "ty

    This extracts [{"claim": "foo", "type": "bar"}] — the one complete item.
    """
    # Find all complete {...} blocks
    items = []
    depth = 0
    start = None
    in_string = False
    escaped = False

    for i, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue

        if char == "{":
            if depth == 0:
                start = i
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    obj = json.loads(text[start:i+1])
                    items.append(obj)
                except json.JSONDecodeError:
                    pass
                start = None

    return items
