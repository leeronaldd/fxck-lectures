"""Stage 2.5: Fact-Check & Exam Grounding.

Extracts key claims from generated explanations, verifies them using
Gemini Flash with Google Search grounding, and checks exam relevance.

Flag-only for v1 — no auto-correction. Measures error rate first.
"""

import json
import sys
import time
from dataclasses import dataclass, asdict

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.config import GCP_PROJECT_ID, GCP_LOCATION, CHUNKER_FALLBACK_MODEL

# ---------------------------------------------------------------------------
# Textbook RAG: fetch relevant chapter from open-access textbooks
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# OpenStax textbook chapter lookup tables
# Hardcoded URLs = 100% reliable, zero LLM calls for URL resolution
# Add new textbooks as needed (anatomy, pharmacology, etc.)
# ---------------------------------------------------------------------------

_OPENSTAX_BASE = "https://openstax.org/books"

TEXTBOOK_CHAPTERS = {
    "microbiology": {
        # Ch 1: Introduction to Microbiology
        "introduction": f"{_OPENSTAX_BASE}/microbiology/pages/1-1-what-our-ancestors-knew",
        "history": f"{_OPENSTAX_BASE}/microbiology/pages/1-2-a-systematic-approach",
        # Ch 2: Microscopy
        "microscopy": f"{_OPENSTAX_BASE}/microbiology/pages/2-1-the-properties-of-light",
        # Ch 3: Cell Structure
        "prokaryotic cells": f"{_OPENSTAX_BASE}/microbiology/pages/3-3-unique-characteristics-of-prokaryotic-cells",
        "eukaryotic cells": f"{_OPENSTAX_BASE}/microbiology/pages/3-4-unique-characteristics-of-eukaryotic-cells",
        "cell wall": f"{_OPENSTAX_BASE}/microbiology/pages/3-3-unique-characteristics-of-prokaryotic-cells",
        "cell membrane": f"{_OPENSTAX_BASE}/microbiology/pages/3-1-spontaneous-generation",
        # Ch 6: Virology
        "virus": f"{_OPENSTAX_BASE}/microbiology/pages/6-1-viruses",
        "viruses": f"{_OPENSTAX_BASE}/microbiology/pages/6-1-viruses",
        "viral structure": f"{_OPENSTAX_BASE}/microbiology/pages/6-1-viruses",
        "viral classification": f"{_OPENSTAX_BASE}/microbiology/pages/6-1-viruses",
        "baltimore": f"{_OPENSTAX_BASE}/microbiology/pages/6-1-viruses",
        "viral life cycle": f"{_OPENSTAX_BASE}/microbiology/pages/6-2-the-viral-life-cycle",
        "viral replication": f"{_OPENSTAX_BASE}/microbiology/pages/6-2-the-viral-life-cycle",
        "lytic": f"{_OPENSTAX_BASE}/microbiology/pages/6-2-the-viral-life-cycle",
        "lysogenic": f"{_OPENSTAX_BASE}/microbiology/pages/6-2-the-viral-life-cycle",
        "bacteriophage": f"{_OPENSTAX_BASE}/microbiology/pages/6-2-the-viral-life-cycle",
        "animal virus": f"{_OPENSTAX_BASE}/microbiology/pages/6-3-isolation-culture-and-identification-of-viruses",
        "viral evolution": f"{_OPENSTAX_BASE}/microbiology/pages/6-1-viruses",
        "viral infection": f"{_OPENSTAX_BASE}/microbiology/pages/6-2-the-viral-life-cycle",
        # Ch 7: Microbial Biochemistry
        "metabolism": f"{_OPENSTAX_BASE}/microbiology/pages/8-1-energy-matter-and-enzymes",
        "enzyme": f"{_OPENSTAX_BASE}/microbiology/pages/8-1-energy-matter-and-enzymes",
        # Ch 9: Microbial Growth
        "bacterial growth": f"{_OPENSTAX_BASE}/microbiology/pages/9-1-how-microbes-grow",
        # Ch 11: Mechanisms of Microbial Genetics
        "genetics": f"{_OPENSTAX_BASE}/microbiology/pages/11-1-the-functions-of-genetic-material",
        "dna replication": f"{_OPENSTAX_BASE}/microbiology/pages/11-2-dna-replication",
        "transcription": f"{_OPENSTAX_BASE}/microbiology/pages/11-3-rna-transcription",
        "translation": f"{_OPENSTAX_BASE}/microbiology/pages/11-4-protein-synthesis-translation",
        # Ch 13: Antimicrobials
        "antibiotic": f"{_OPENSTAX_BASE}/microbiology/pages/14-1-history-of-chemotherapy-and-antimicrobial-discovery",
        "antimicrobial": f"{_OPENSTAX_BASE}/microbiology/pages/14-2-fundamentals-of-antimicrobial-chemotherapy",
        # Ch 15: Immune System
        "immune": f"{_OPENSTAX_BASE}/microbiology/pages/17-1-innate-nonspecific-host-defenses",
        "inflammation": f"{_OPENSTAX_BASE}/microbiology/pages/17-4-inflammation-and-fever",
    },
    "anatomy": {
        "muscle": f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/10-1-overview-of-muscle-tissues",
        "muscle contraction": f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/10-3-muscle-fiber-contraction-and-relaxation",
        "skeletal": f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/6-1-the-functions-of-the-skeletal-system",
        "bone": f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/6-3-bone-structure",
        "neuron": f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/12-1-basic-structure-and-function-of-the-nervous-system",
        "action potential": f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/12-4-the-action-potential",
        "cardiac": f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/19-1-heart-anatomy",
        "respiratory": f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/22-1-organs-and-structures-of-the-respiratory-system",
    },
}


def fetch_textbook_chapter(topic_name: str, subject: str = "microbiology") -> str | None:
    """Fetch the most relevant textbook chapter for a topic.

    Uses a hardcoded lookup table for 100% reliability — zero LLM calls
    for URL resolution. Matches topic keywords against chapter entries.

    Returns the chapter text (up to 5000 chars) or None if not found.
    """
    import urllib.request
    import re

    # Step 1: Look up the right chapter URL from the table
    chapters = TEXTBOOK_CHAPTERS.get(subject, TEXTBOOK_CHAPTERS.get("microbiology", {}))
    topic_lower = topic_name.lower()

    url = None
    # Try exact keyword matches first, then partial
    for keyword, chapter_url in chapters.items():
        if keyword in topic_lower:
            url = chapter_url
            break

    # Broader match: check if any chapter keyword appears in the topic
    if not url:
        for keyword, chapter_url in chapters.items():
            if any(word in topic_lower for word in keyword.split()):
                url = chapter_url
                break

    if not url:
        print(f"    No textbook chapter mapped for '{topic_name}'")
        return None

    # Step 2: Fetch the chapter page
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode("utf-8")
    except Exception as e:
        print(f"    Failed to fetch {url}: {e}")
        return None

    # Step 3: Extract text content
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    # Find actual content start
    for marker in ["Learning Objectives", "By the end of this section", "Introduction"]:
        start = text.find(marker)
        if start > 0:
            text = text[start:]
            break

    # Cap at 5000 chars (enough context for fact-checking, saves tokens)
    chapter_text = text[:5000].strip()
    if chapter_text:
        print(f"    Fetched textbook: {url[:60]}... ({len(chapter_text)} chars)")
    return chapter_text if chapter_text else None


@dataclass
class ClaimVerification:
    claim: str
    claim_type: str                  # mechanism, association, statistic, classification
    source_group: str                # which concept group this came from
    verdict: str                     # correct, wrong, unverifiable
    correction: str = ""             # if wrong, what's the correct info
    sources: list[str] | None = None # URLs from search results
    exam_relevant: bool = True       # is this commonly assessed?
    exam_notes: str = ""             # notes on exam relevance


def extract_claims(explanation_text: str, topic_name: str) -> list[dict]:
    """Use Flash to extract key factual claims from an explanation.

    Returns 3-5 claims per section — focuses on things that could be wrong:
    organism-disease associations, mechanism steps, statistics, classifications.
    """
    from google import genai

    prompt = (
        f"From this student explanation about '{topic_name}', extract 3-5 key factual claims "
        "that could potentially be wrong. Focus on:\n"
        "- Organism-disease associations\n"
        "- Mechanism steps or process ordering\n"
        "- Statistics or numbers\n"
        "- Classification details\n\n"
        "Return ONLY a JSON array:\n"
        '[{"claim": "the factual claim", "type": "association|mechanism|statistic|classification"}]\n\n'
        f'EXPLANATION:\n"""\n{explanation_text[:2000]}\n"""'
    )

    client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)

    from src.json_repair import extract_json

    response = client.models.generate_content(
        model=CHUNKER_FALLBACK_MODEL,
        contents=prompt,
        config={"temperature": 0.1, "max_output_tokens": 1024},
    )

    return extract_json(response.text, expect_array=True)


def verify_claim(claim: str, topic_name: str) -> dict:
    """Verify a single claim using Gemini Flash with Google Search grounding.

    Returns verdict + sources + exam relevance.
    """
    from google import genai
    from google.genai import types

    prompt = (
        f"Verify this medical/scientific claim and assess its exam relevance:\n\n"
        f"CLAIM: \"{claim}\"\n"
        f"TOPIC: {topic_name}\n\n"
        "Answer these two questions:\n"
        "1. Is this claim factually accurate? If wrong, what's the correction?\n"
        "2. Is this topic commonly assessed in 1st-year biomedical science exams?\n\n"
        "Return ONLY a JSON object:\n"
        '{"verdict": "correct|wrong|unverifiable", "correction": "only if wrong", '
        '"exam_relevant": true/false, "exam_notes": "brief note on exam relevance"}'
    )

    client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)
    response = client.models.generate_content(
        model=CHUNKER_FALLBACK_MODEL,
        contents=prompt,
        config={
            "tools": [types.Tool(google_search=types.GoogleSearch())],
            "temperature": 0.1,
            "max_output_tokens": 512,
        },
    )

    # Extract sources from grounding metadata
    sources = []
    if hasattr(response, "candidates") and response.candidates:
        cand = response.candidates[0]
        if hasattr(cand, "grounding_metadata") and cand.grounding_metadata:
            gm = cand.grounding_metadata
            if hasattr(gm, "grounding_chunks") and gm.grounding_chunks:
                for chunk in gm.grounding_chunks[:3]:
                    if hasattr(chunk, "web") and chunk.web:
                        title = getattr(chunk.web, "title", "")
                        uri = getattr(chunk.web, "uri", "")
                        if title or uri:
                            sources.append(f"{title}: {uri}" if title else uri)

    # Parse the response
    from src.json_repair import extract_json
    result = extract_json(response.text, expect_array=False)
    if not result or not isinstance(result, dict):
        result = {"verdict": "unverifiable", "correction": "", "exam_relevant": True, "exam_notes": ""}

    result["sources"] = sources
    return result


def verify_section(explanation_text: str, topic_name: str,
                    textbook_context: str | None = None) -> list[dict]:
    """Verify ALL factual claims in a section.

    Primary: uses textbook chapter as ground truth (if available).
    Fallback: uses Flash + Google Search grounding.

    Returns list of error dicts: [{"claim": "...", "correction": "...", "type": "..."}]
    """
    from google import genai
    from google.genai import types
    from src.json_repair import extract_json

    # Build the verification context
    if textbook_context:
        context_block = (
            f"TEXTBOOK REFERENCE (use this as the PRIMARY source of truth):\n"
            f'"""\n{textbook_context[:4000]}\n"""\n\n'
        )
        source_instruction = (
            "Verify ALL claims in the student explanation against the TEXTBOOK REFERENCE above. "
            "The textbook is the authoritative source. If the student explanation contradicts "
            "the textbook, flag it as wrong. Use web search only for claims not covered by the textbook."
        )
    else:
        context_block = ""
        source_instruction = (
            "Verify ALL factual claims against web sources. "
            "Only trust reputable medical/academic sources (NIH, PubMed, NCBI, university textbooks, WHO)."
        )

    prompt = (
        f"You are a medical fact-checker. Read this student explanation about '{topic_name}' "
        f"and verify ALL factual claims.\n\n"
        f"{source_instruction}\n\n"
        f"{context_block}"
        "Check for:\n"
        "- Wrong organism-disease associations\n"
        "- Incorrect mechanism steps or classification details\n"
        "- Wrong statistics or numbers\n"
        "- Misleading simplifications that would cause exam errors\n\n"
        "Also note: is each major topic in this section commonly assessed in "
        "1st-year biomedical science exams?\n\n"
        "Return a JSON array of findings. For CORRECT claims, don't include them. "
        "Only include ERRORS and EXAM RELEVANCE notes:\n"
        '[{"claim": "the wrong claim text", "verdict": "wrong", "correction": "what it should say", "type": "mechanism"},\n'
        ' {"claim": "topic X", "verdict": "exam_note", "exam_relevant": true, "exam_notes": "commonly tested"}]\n\n'
        "If everything is correct, return []\n\n"
        f'STUDENT EXPLANATION:\n"""\n{explanation_text[:3000]}\n"""'
    )

    client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)
    response = client.models.generate_content(
        model=CHUNKER_FALLBACK_MODEL,
        contents=prompt,
        config={
            "tools": [types.Tool(google_search=types.GoogleSearch())],
            "temperature": 0.1,
            "max_output_tokens": 2048,
        },
    )

    # Extract sources from grounding metadata
    sources = []
    if hasattr(response, "candidates") and response.candidates:
        cand = response.candidates[0]
        if hasattr(cand, "grounding_metadata") and cand.grounding_metadata:
            gm = cand.grounding_metadata
            if hasattr(gm, "grounding_chunks") and gm.grounding_chunks:
                for chunk in gm.grounding_chunks[:5]:
                    if hasattr(chunk, "web") and chunk.web:
                        title = getattr(chunk.web, "title", "")
                        uri = getattr(chunk.web, "uri", "")
                        if title or uri:
                            sources.append(f"{title}: {uri}" if title else uri)

    findings = extract_json(response.text, expect_array=True)

    # Attach sources to all findings
    for f in findings:
        if "sources" not in f:
            f["sources"] = sources

    return findings


def verify_and_ground(
    explanations: list[dict],
    groups: list,
) -> tuple[list[dict], list[ClaimVerification]]:
    """Run comprehensive fact-check + exam grounding on all generated explanations.

    Sends the ENTIRE explanation text to Flash with Google Search grounding
    in one call per section. Flash reads everything and flags errors.
    No random sampling — checks all claims.

    Returns (corrected_explanations, verification_report).
    Detects errors AND corrects them using Pro for surgical paragraph rewrites.
    """
    from src.config import GENERATOR_MODEL

    all_verifications = []

    for expl in explanations:
        if expl.get("was_skipped") or not expl.get("explanation_text"):
            continue

        topic = expl.get("topic_name", "Unknown")
        text = expl.get("explanation_text", "")

        if len(text.split()) < 50:
            continue

        print(f"  Checking: {topic}")

        # Fetch relevant textbook chapter for this topic
        textbook = None
        try:
            textbook = fetch_textbook_chapter(topic)
        except Exception as e:
            print(f"    Textbook fetch failed: {e}")

        try:
            findings = verify_section(text, topic, textbook_context=textbook)
            time.sleep(1)  # rate limiting between sections
        except Exception as e:
            print(f"    Verification failed: {e}")
            continue

        errors = [f for f in findings if f.get("verdict") == "wrong"]
        exam_notes = [f for f in findings if f.get("verdict") == "exam_note"]

        if errors:
            for err in errors:
                print(f"    ❌ {err.get('claim', '?')[:60]}")
                all_verifications.append(ClaimVerification(
                    claim=err.get("claim", ""),
                    claim_type=err.get("type", "unknown"),
                    source_group=topic,
                    verdict="wrong",
                    correction=err.get("correction", ""),
                    sources=err.get("sources", []),
                    exam_relevant=True,
                ))

            # Correct errors using Pro — surgical paragraph rewrites
            corrected_text = _correct_errors_with_pro(
                text, errors, topic, GENERATOR_MODEL
            )
            if corrected_text and len(corrected_text.split()) > len(text.split()) * 0.5:
                expl["explanation_text"] = corrected_text
                expl["word_count"] = len(corrected_text.split())
                print(f"    ✏️ Corrected {len(errors)} errors")
            else:
                print(f"    ⚠️ Correction failed — keeping original")
        else:
            print(f"    ✅ All claims verified")

        for note in exam_notes:
            all_verifications.append(ClaimVerification(
                claim=note.get("claim", ""),
                claim_type="exam_relevance",
                source_group=topic,
                verdict="correct",
                exam_relevant=note.get("exam_relevant", True),
                exam_notes=note.get("exam_notes", ""),
            ))

    return explanations, all_verifications


def _correct_errors_with_pro(
    explanation_text: str,
    errors: list[dict],
    topic_name: str,
    model: str,
) -> str | None:
    """Use Gemini Pro to surgically rewrite paragraphs containing factual errors.

    For each error, finds the paragraph containing it and rewrites JUST that paragraph
    with the correct information. Includes voice rules so the fix matches the
    colloquial tone of the surrounding text.

    Returns corrected full text, or None if correction failed.
    """
    from google import genai

    # Build correction instructions
    corrections = []
    for err in errors:
        claim = err.get("claim", "")
        correction = err.get("correction", "")
        if claim and correction:
            corrections.append(f"WRONG: \"{claim}\"\nCORRECT: {correction}")

    if not corrections:
        return None

    prompt = (
        f"You are fixing factual errors in a student explanation about '{topic_name}'.\n\n"
        "VOICE RULES (maintain this tone in your rewrites):\n"
        "- Write like a friend explaining over coffee. Contractions always.\n"
        "- Use 'we', 'our', 'you'd'. Keep sentences short and punchy.\n"
        "- The correction should sound like a tutor catching a mistake, "
        "not a textbook issuing a correction notice.\n"
        "- Do NOT add hedging words (generally, typically, relatively) unless essential.\n\n"
        "ERRORS TO FIX:\n" + "\n\n".join(corrections) + "\n\n"
        "INSTRUCTIONS:\n"
        "- Find the paragraph(s) containing each error\n"
        "- Rewrite ONLY those paragraphs with the correct information\n"
        "- Keep all other paragraphs EXACTLY as they are — do not touch them\n"
        "- Maintain the same casual, engaging tone throughout\n"
        "- Return the COMPLETE explanation text with fixes applied\n\n"
        f'CURRENT EXPLANATION:\n"""\n{explanation_text}\n"""'
    )

    client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={"temperature": 0.3, "max_output_tokens": 8192},
        )
        return (response.text or "").strip()
    except Exception as e:
        print(f"    Correction failed: {e}")
        return None


def format_verification_report(verifications: list[ClaimVerification]) -> str:
    """Format verification results as human-readable report."""
    if not verifications:
        return "No claims to verify."

    correct = [v for v in verifications if v.verdict == "correct"]
    wrong = [v for v in verifications if v.verdict == "wrong"]
    unverifiable = [v for v in verifications if v.verdict == "unverifiable"]
    exam_relevant = [v for v in verifications if v.exam_relevant]

    lines = [
        f"Verification Report: {len(verifications)} claims checked\n",
        f"  ✅ Correct: {len(correct)}",
        f"  ❌ Wrong: {len(wrong)}",
        f"  ❓ Unverifiable: {len(unverifiable)}",
        f"  📝 Exam-relevant: {len(exam_relevant)}/{len(verifications)}",
    ]

    if wrong:
        lines.append("\nERRORS FOUND:")
        for v in wrong:
            lines.append(f"  ❌ {v.claim}")
            lines.append(f"     Correction: {v.correction}")
            lines.append(f"     Source: {v.source_group}")
            if v.sources:
                lines.append(f"     References: {v.sources[0]}")

    return "\n".join(lines)


def save_verification_report(verifications: list[ClaimVerification], output_path: str):
    """Save verification report to JSON."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([asdict(v) for v in verifications], f, indent=2, ensure_ascii=False)
    print(f"Saved verification report ({len(verifications)} claims) to {output_path}")
