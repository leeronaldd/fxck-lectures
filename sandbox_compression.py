"""Sandbox: test different prompting methods to compress Pro on low-EI content."""

import json
import time
import sys
import os

sys.path.insert(0, "src")
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from google import genai
from config import GCP_PROJECT_ID, GCP_LOCATION, GENERATOR_MODEL
from generator_v2 import build_system_instruction_text, build_creative_brief_image_parts

client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)

# Load the chunk
chunks = json.load(open("data/output/final_chunks_v5.json", encoding="utf-8"))
CHUNK = chunks[12]  # Animal Virus Families
TRANSCRIPT = CHUNK["transcript_text"]
TOPIC = CHUNK["topic_name"]

# System instruction (same creative brief for all tests)
SYSTEM = build_system_instruction_text()


def run_test(test_name: str, user_prompt: str, max_tokens: int = 4096) -> tuple[str, int]:
    """Run one generation test and return (output_text, word_count)."""
    from google.genai import types

    parts = build_creative_brief_image_parts()
    parts.append(types.Part.from_text(text=user_prompt))

    try:
        response = client.models.generate_content(
            model=GENERATOR_MODEL,
            contents=parts,
            config={
                "system_instruction": SYSTEM,
                "temperature": 0.7,
                "max_output_tokens": max_tokens,
                "tools": [{"google_search": {}}],
            },
        )
        text = response.text
        # Extract just the transcript portion
        import re
        match = re.search(r"=== TRANSCRIPT ===\s*(.+?)(?=\n=== EI%|$)", text, re.DOTALL)
        transcript_only = match.group(1).strip() if match else text
        wc = len(transcript_only.split())
        return transcript_only, wc
    except Exception as e:
        return f"[ERROR: {e}]", 0


# ══════════════════════════════════════════════════════════════
# TEST METHODS
# ══════════════════════════════════════════════════════════════

TESTS = {}

# Method 1: BASELINE — full transcript, no depth guidance (what Run 8 does)
TESTS["1_baseline"] = f"""PROFESSOR'S TRANSCRIPT FOR THIS SECTION (topic: '{TOPIC}').
Use this for WHAT to teach, not HOW. The transcript is auto-captioned and full of garbled terms.

{TRANSCRIPT}

Write this as Slide 11.
Output in this exact format:

=== SLIDE ===
Slide 11: [Your title]
type: professor_slide OR diagram
[slide content]

=== TRANSCRIPT ===
Slide 11
[Your transcript — written exactly how the anatomy professor writes]

=== EI% ===
[0-100]% — [One sentence: why this score.]"""

# Method 2: WORD LIMIT — explicit "keep under 150 words"
TESTS["2_word_limit"] = f"""PROFESSOR'S TRANSCRIPT FOR THIS SECTION (topic: '{TOPIC}').
Use this for WHAT to teach, not HOW.

{TRANSCRIPT}

DEPTH GUIDANCE: This section scored EI 50% — supporting knowledge. Keep the transcript to 100-150 words maximum. A clear overview is enough.

Write this as Slide 11. Output format:
=== SLIDE === / === TRANSCRIPT === / === EI% ==="""

# Method 3: STYLE HINT — "like naming bone markings"
TESTS["3_style_hint"] = f"""PROFESSOR'S TRANSCRIPT FOR THIS SECTION (topic: '{TOPIC}').
Use this for WHAT to teach, not HOW.

{TRANSCRIPT}

DEPTH GUIDANCE: This section scored EI 50% — supporting knowledge.
STYLE: This is like the anatomy professor's muscle types comparison slide — quick, confident overview. One dense paragraph listing the key families with their clinical significance embedded. No step-by-step mechanisms. The slide does the teaching, the transcript connects the dots.

Write this as Slide 11. Output format:
=== SLIDE === / === TRANSCRIPT === / === EI% ==="""

# Method 4: TRUNCATED TRANSCRIPT — only give 200 chars
TESTS["4_truncated"] = f"""SECTION SUMMARY (topic: '{TOPIC}').
This is a low-priority section (EI 50%). Brief overview of major animal virus families:
DNA: Papillomaviridae (HPV), Herpesviridae, Hepadnaviridae, Poxviridae.
RNA: Picornaviridae (polio), Caliciviridae (norovirus), Flaviviridae (dengue, Zika).

Cover these briefly — a sentence or two each, or a comparison table. Don't teach mechanisms.

Write this as Slide 11. Output format:
=== SLIDE === / === TRANSCRIPT === / === EI% ==="""

# Method 5: MAX_TOKENS CAP — hard 1024 token limit
TESTS["5_token_cap"] = TESTS["1_baseline"]  # Same prompt, different max_tokens

# Method 6: ROLE FRAMING — "you're writing a bridge paragraph"
TESTS["6_bridge"] = f"""PROFESSOR'S TRANSCRIPT FOR THIS SECTION (topic: '{TOPIC}').

{TRANSCRIPT}

You are writing a BRIDGE PARAGRAPH — not a teaching section. This is the anatomy professor between major topics. She'd say something like: "Looking at the table on the slide, you can see the major DNA families up top — papilloma, herpes, pox — and the RNA families below. Notice that most of the clinically severe infections come from the RNA side. We'll come back to specific families when we cover how these viruses actually enter and hijack animal cells."

That's it. 2-4 sentences. The slide has the table. You're just pointing at it and moving on.

Write this as Slide 11. Output format:
=== SLIDE === / === TRANSCRIPT === / === EI% ==="""

# Method 7: COMBINED — truncated source + bridge framing + token cap
TESTS["7_combined"] = f"""SECTION SUMMARY (topic: '{TOPIC}').
DNA families: Papillomaviridae (HPV/cancer), Herpesviridae (chickenpox, cold sores), Hepadnaviridae (Hep B), Poxviridae (smallpox).
RNA families: Picornaviridae (polio), Caliciviridae (norovirus), Flaviviridae (dengue, Zika).

Write a bridge paragraph — 2-4 sentences pointing at the slide and moving on. The slide has the full table. You're connecting this to the next section on animal virus entry mechanisms.

Write this as Slide 11. Output format:
=== SLIDE === / === TRANSCRIPT === / === EI% ==="""


# ══════════════════════════════════════════════════════════════
# RUN ALL TESTS
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"Testing {len(TESTS)} compression methods on: {TOPIC}")
    print(f"Professor transcript: {len(TRANSCRIPT.split())} words")
    print("=" * 60)

    results = {}
    for name, prompt in TESTS.items():
        max_tok = 1024 if name == "5_token_cap" else 4096
        print(f"\n{'─' * 60}")
        print(f"TEST: {name} (max_tokens={max_tok})")
        print(f"{'─' * 60}")

        t0 = time.time()
        text, wc = run_test(name, prompt, max_tokens=max_tok)
        elapsed = time.time() - t0

        results[name] = wc
        print(f"  Words: {wc} ({elapsed:.1f}s)")
        print(f"  Output: {text[:300]}...")

    print(f"\n{'=' * 60}")
    print("RESULTS SUMMARY")
    print(f"{'=' * 60}")
    for name, wc in sorted(results.items(), key=lambda x: x[1]):
        bar = "█" * (wc // 20) + "░" * max(0, 25 - wc // 20)
        print(f"  {name:<20} {wc:>4}w  {bar}")
