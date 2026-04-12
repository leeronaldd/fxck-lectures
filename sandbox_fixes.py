"""Sandbox: test fixes for remaining issues one by one.

Issue 1: Hard constraint over-constraining (Animal Entry = 117w despite EI 92%)
Issue 2: Repetition not fully eliminated (lytic 6x, Baltimore 5x)
Issue 3: Garbled terms slipping through
"""

import json, sys, time, re, os
sys.path.insert(0, "src")
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from google import genai
from google.genai import types
from config import GCP_PROJECT_ID, GCP_LOCATION, GENERATOR_MODEL
from generator_v2 import build_system_instruction_text, build_creative_brief_image_parts

client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)
SYSTEM = build_system_instruction_text()

chunks = json.load(open("data/output/final_chunks_v5.json", encoding="utf-8"))


def run_pro(prompt_text, max_tokens=4096):
    parts = build_creative_brief_image_parts()
    parts.append(types.Part.from_text(text=prompt_text))
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
    match = re.search(r"=== TRANSCRIPT ===\s*(.+?)(?=\n=== EI%|$)", text, re.DOTALL)
    transcript = match.group(1).strip() if match else text
    return transcript, len(transcript.split())


OUTPUT_FMT = """Write this as Slide {n}. Output in this exact format:
=== SLIDE ===
Slide {n}: [Your title]
type: professor_slide OR diagram
[slide content]

=== TRANSCRIPT ===
Slide {n}
[Your transcript]

=== EI% ===
[0-100]% - [One sentence]"""


def test_issue(issue_name, tests):
    print(f"\n{'='*60}")
    print(f"ISSUE: {issue_name}")
    print(f"{'='*60}")
    results = {}
    for name, prompt in tests.items():
        print(f"\n  Testing: {name}...")
        t0 = time.time()
        try:
            transcript, wc = run_pro(prompt)
            elapsed = time.time() - t0
            results[name] = {"wc": wc, "text": transcript, "time": elapsed}
            print(f"    {wc}w ({elapsed:.0f}s)")
            print(f"    Preview: {transcript[:200]}...")
        except Exception as e:
            print(f"    ERROR: {e}")
            results[name] = {"wc": 0, "text": str(e), "time": 0}
    return results


# ================================================================
# ISSUE 1: Over-constraining high-EI sections
# ================================================================

chunk13 = chunks[13]
transcript13 = chunk13["transcript_text"]
topic13 = chunk13["topic_name"]

ISSUE1_TESTS = {}

# Test A: Massive ALREADY TAUGHT list (current broken approach)
ISSUE1_TESTS["A_massive_list"] = (
    "ALREADY TAUGHT IN EARLIER SLIDES - DO NOT RE-EXPLAIN:\n"
    "- Slide 1: Viral architecture, capsid types, nucleocapsid\n"
    "- Slide 2: Lipid envelope, spike proteins, budding\n"
    "- Slide 3: Virus size ranges, RNA vs DNA genome correlation\n"
    "- Slide 4: ICTV taxonomy, suffix conventions\n"
    "- Slide 5: Geographic naming, pathologic naming, morphologic naming\n"
    "- Slide 6: Baltimore classification overview, 7 classes, mRNA goal\n"
    "- Slide 7: Baltimore Classes I-VII individual mechanisms\n"
    "- Slide 8: Viral evolution hypotheses\n"
    "- Slide 9: Bacteriophage injection, lysozyme, ghost shells\n"
    "- Slide 10: Lytic cycle 5 steps, lysogenic cycle, viral oncogenesis\n"
    "- Slide 11: DNA and RNA virus family table\n\n"
    "Reference as 'as we covered earlier' but do NOT re-explain.\n\n"
    f"PROFESSOR'S TRANSCRIPT FOR THIS SECTION (topic: '{topic13}').\n"
    f"{transcript13}\n\n"
    f"{OUTPUT_FMT.format(n=12)}"
)

# Test B: Only RELEVANT overlapping concepts
ISSUE1_TESTS["B_relevant_only"] = (
    "ALREADY TAUGHT - DO NOT RE-EXPLAIN:\n"
    "- Bacteriophage injection mechanism (Slide 9) - genome-only entry through cell wall\n"
    "- Lytic cycle 5 steps (Slide 10) - don't re-walk the steps\n\n"
    "WHAT IS NEW IN THIS SECTION:\n"
    "- How ANIMAL viruses enter cells (different from bacteriophages - whole virus enters)\n"
    "- Receptor-mediated endocytosis vs membrane fusion vs channel formation\n"
    "- Uncoating - how the capsid is stripped inside the cell\n"
    "- Tissue tropism - why specific viruses infect specific tissues\n\n"
    f"PROFESSOR'S TRANSCRIPT FOR THIS SECTION (topic: '{topic13}').\n"
    f"{transcript13}\n\n"
    f"{OUTPUT_FMT.format(n=12)}"
)

# Test C: Checklist only, no constraint
ISSUE1_TESTS["C_checklist_only"] = (
    "PREVIOUSLY COVERED: Slides 1-11 covered viral structure, Baltimore, "
    "bacteriophage infection, lytic/lysogenic cycles.\n"
    "Connect backwards naturally where relevant.\n\n"
    "DEPTH GUIDANCE:\n"
    "This section scored EI 92% - core curriculum.\n\n"
    "SUB-CONCEPTS TO COVER (each needs its own paragraph):\n"
    "  1. Animal virus entry differs from bacteriophages - whole virus enters\n"
    "  2. Receptor-mediated endocytosis - host cell engulfs virus in a vesicle\n"
    "  3. Membrane fusion - enveloped virus merges with host membrane (HIV, Hendra)\n"
    "  4. Channel formation - non-enveloped virus creates a pore\n"
    "  5. Uncoating - capsid stripped by host/viral enzymes to release genome\n"
    "  6. Tissue tropism - receptor specificity dictates which cells infected\n\n"
    f"PROFESSOR'S TRANSCRIPT FOR THIS SECTION (topic: '{topic13}').\n"
    f"{transcript13}\n\n"
    f"{OUTPUT_FMT.format(n=12)}"
)


# ================================================================
# ISSUE 2: Repetition not eliminated
# ================================================================

chunk10 = chunks[10]
transcript10 = chunk10["transcript_text"]
topic10 = chunk10["topic_name"]

ISSUE2_TESTS = {}

# Test A: Hard constraint (current)
ISSUE2_TESTS["A_hard_constraint"] = (
    "ALREADY TAUGHT - DO NOT RE-EXPLAIN:\n"
    "- Lytic cycle 5 steps (attachment, penetration, synthesis, assembly, lysis) - Slide 7\n"
    "- Lysogenic cycle + prophage integration - Slide 7\n"
    "- Baltimore Classes I-VII - Slides 5-6\n\n"
    "WHAT IS NEW: Physical injection mechanism, tail fiber specificity, "
    "lysozyme breach, genome-only entry, ghost shells.\n\n"
    "Open with a 1-sentence callback to Slide 7, then teach ONLY the injection mechanism.\n\n"
    f"PROFESSOR'S TRANSCRIPT FOR THIS SECTION (topic: '{topic10}').\n"
    f"{transcript10}\n\n"
    f"{OUTPUT_FMT.format(n=9)}"
)

# Test B: "ONE JOB" framing
ISSUE2_TESTS["B_one_job"] = (
    "CONTEXT: The student already learned the lytic cycle (5 steps), "
    "lysogenic cycle, and Baltimore classes in previous slides.\n\n"
    "YOUR SECTION HAS ONE JOB: Teach how a bacteriophage physically injects "
    "its genome through a bacterial cell wall. That is it.\n\n"
    "The new content is:\n"
    "1. Tail fibers bind to specific receptors (flagella, pili, transport proteins)\n"
    "2. Lysozyme enzyme breaches the peptidoglycan wall\n"
    "3. Sheath contracts, hollow tube drives through - genome shoots in\n"
    "4. Empty capsid remains outside (ghost shell)\n"
    "5. Electron micrograph shows assembled phages packing the cytoplasm\n\n"
    'Open with: "We covered the 5 steps of the lytic cycle in Slide 7. '
    'Now let us zoom into Step 2 and see the physical mechanics."\n\n'
    f"PROFESSOR'S TRANSCRIPT FOR THIS SECTION (topic: '{topic10}').\n"
    f"{transcript10}\n\n"
    f"{OUTPUT_FMT.format(n=9)}"
)

# Test C: Redacted transcript (remove lytic content from source)
lytic_redacted = re.sub(
    r"(?i)(?:attachment|penetration|synthesis|assembly|lysis|lytic cycle|lysogenic|prophage)[^.]*\.",
    "",
    transcript10
)
ISSUE2_TESTS["C_redacted_source"] = (
    "PREVIOUSLY COVERED: Lytic cycle, lysogenic cycle, Baltimore classes.\n\n"
    f"PROFESSOR'S TRANSCRIPT FOR THIS SECTION (topic: '{topic10}').\n"
    "[Note: Lytic/lysogenic content removed - already covered. Focus on injection mechanism.]\n\n"
    f"{lytic_redacted}\n\n"
    f"{OUTPUT_FMT.format(n=9)}"
)


# ================================================================
# ISSUE 3: Garbled terms
# ================================================================

def test_term_filter():
    print(f"\n{'='*60}")
    print("ISSUE 3: Garbled Term Filter")
    print(f"{'='*60}")

    _TRAILING_FILLER = re.compile(
        r"\s+(?:if|and|but|or|the|a|an|is|are|was|were|which|that|this|"
        r"so|um|uh|okay|very|also|has|have|it|its|with|for|from|"
        r"can|will|do|does|did|not|no|be|been|being|more|most|"
        r"here|there|some|into|of|in|on|at|to|as|we|our|they)$",
        re.IGNORECASE,
    )

    all_terms = []
    for c in chunks:
        all_terms.extend(c.get("key_terms", []))

    print(f"\n  Total key terms: {len(all_terms)}")
    print(f"\n  Garbled terms fixed:")
    fixed = 0
    for t in all_terms:
        cleaned = _TRAILING_FILLER.sub("", t).strip()
        if cleaned != t and cleaned:
            print(f"    '{t}' -> '{cleaned}'")
            fixed += 1

    # Also show terms that are clearly sentence fragments
    print(f"\n  Suspicious multi-word terms (possible fragments):")
    for t in all_terms:
        words = t.split()
        if len(words) >= 3:
            print(f"    '{t}'")

    print(f"\n  Fixed: {fixed} terms")


if __name__ == "__main__":
    run_issues = [a.lower() for a in sys.argv[1:]] if len(sys.argv) > 1 else ["1", "2", "3"]

    if "1" in run_issues:
        r1 = test_issue("Over-constraining (Animal Entry EI 92%)", ISSUE1_TESTS)
        print(f"\n  SUMMARY - Issue 1:")
        for name, data in sorted(r1.items(), key=lambda x: x[1]["wc"]):
            print(f"    {name:<25} {data['wc']:>4}w")

    if "2" in run_issues:
        r2 = test_issue("Repetition (Prokaryotic Infection)", ISSUE2_TESTS)
        print(f"\n  SUMMARY - Issue 2:")
        for name, data in sorted(r2.items()):
            lytic_count = len(re.findall(
                r"lytic cycle|5.step|attachment.*penetration.*synthesis|AP.?SAR",
                data["text"], re.IGNORECASE
            ))
            print(f"    {name:<25} {data['wc']:>4}w  lytic re-explanations: {lytic_count}")

    if "3" in run_issues:
        test_term_filter()
