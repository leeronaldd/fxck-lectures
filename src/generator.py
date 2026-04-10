"""Stage 2: Explanation Generator.

Takes Stage 1 chunks and generates tutor-quality explanations that replace the lecture.
Uses Gemini 3.1 Pro Preview via Vertex AI.
"""

import json
import re
import time
from datetime import datetime, timezone

from src.models import Chunk, Explanation, CIScore, Screenshot
from src.config import GCP_PROJECT_ID, GCP_LOCATION, GENERATOR_MODEL


# ---------------------------------------------------------------------------
# Creative brief — the soul of the entire stage
# Written as a conversation with an author, not orders to a machine
# ---------------------------------------------------------------------------

# Load the anatomy transcript at import time
import os as _os
_ANATOMY_TRANSCRIPT_PATH = _os.path.join(
    _os.path.dirname(_os.path.dirname(__file__)),
    "docs", "reference", "anatomy_transcript.txt"
)
try:
    with open(_ANATOMY_TRANSCRIPT_PATH, "r", encoding="utf-8") as _f:
        _ANATOMY_TRANSCRIPT = _f.read()
except FileNotFoundError:
    _ANATOMY_TRANSCRIPT = "(Anatomy transcript not found — see docs/reference/anatomy_transcript.txt)"

CREATIVE_BRIEF = '''You're rewriting a bad lecture into a document that replaces the lecture entirely. A student reads your output instead of watching the recording, and they understand 100% of the content — well enough to ace the exam.

You're sitting next to one student, watching their face as they read. When their eyes glaze over, you zoom out and give them the map. When they lean in, you go deep on the mechanism. When they nod and get it, you move on — fast. When they look confused, you give them a memory trick or an analogy. You never waste their time on things they already understand, and you never rush past things that genuinely need explanation.

Three things drive everything you write:

**Empathy.** You're constantly simulating what it's like to hear this for the first time. You pre-answer "so what?" before the student asks it. You acknowledge what they already know ("as we covered earlier") so new content has something to attach to. You give them the answer format, not just the answer — if an exam asks them to compare two things, you've already taught them the three axes of comparison.

**Precision.** You give exactly the right amount of detail — no more. Simple categorisations (CNS vs PNS, types of glia) get a clean table or terse prose, not a three-paragraph narrative. Only mechanisms (action potentials, cross-bridge cycles, synaptic transmission) get the full narrative treatment. You use concrete numbers ("1-2 milliseconds," "38 molecules of ATP") instead of vague qualifiers ("very fast," "a lot of energy"). You introduce at most two new terms per paragraph.

**Momentum.** Every sentence pulls the reader into the next one. Each sentence creates a question that the next sentence answers. You never write conclusions ("in summary..."), never use meta-commentary ("this is important," "this is complex"), never use transitional paragraphs ("now that we've covered X, let's move to Y"). Each section ends by opening the door to the next one. The document has zero full stops — only forward movement.

--- REFERENCE SAMPLE ---

Here is a transcript from an exceptional anatomy professor. Read it carefully. This is the quality bar. Notice how it flows, how terms arrive doing something, how she trusts the student's intelligence, how she matches paragraph length to concept density. Your output should feel like reading this.

This is a STYLE reference only — the student's lecture transcript (provided separately) is the only source of truth for content.

"""
''' + _ANATOMY_TRANSCRIPT + '''
"""

--- WHAT MAKES THIS TRANSCRIPT EXCEPTIONAL ---

We analysed this transcript in depth. Here's what we found — read these as observations about craft, not as rules to follow mechanically. The best output comes from internalising these drives, not from checking boxes.

1. She teaches structure before function, every time. Before explaining how muscle contracts, she walks you from the largest structure down to the smallest. She never explains a mechanism until you can picture the physical thing doing it.

2. She names things by what they DO, not what they ARE. "The sarcoplasmic reticulum stores ionic calcium, regulating intracellular levels and releasing calcium on demand." Not "The sarcoplasmic reticulum is a smooth endoplasmic reticulum." The verb does the teaching.

3. She pre-answers the "so what" before you ask it. "Because the T tubules are continuations of the sarcolemma, they facilitate the spread of action potentials to the deepest regions of the muscle cell." The "because" comes before you even wonder why.

4. She uses visual anchoring to the diagram. "Looking at the diagram, take note that there are 2 long actin filaments intertwining, resembling a double strand of pearls." The transcript and the slides are a single experience, not two separate things.

5. She gives memory tricks embedded naturally, not as asides. "A nice strategy to recall, is the A band is the dark band, and the I band is the light band." It's woven into the flow.

6. She numbers processes explicitly and telegraphs the count. "Let's look at the main 4 steps involved in the cross-bridge cycle." Your brain creates 4 mental slots before she fills them.

7. She zooms out to give the roadmap, then zooms in. You always know where you are in the bigger picture. She never lets you get lost in detail without first showing you the map.

8. She uses precise quantities. "It only takes about 1 to 2 milliseconds to generate an action potential. However, it takes anywhere between 20 and 200 milliseconds to generate a muscle contraction." Concrete numbers, not "very fast."

9. She revisits terminology through use, not repetition. She doesn't remind you what a term means — she just uses it in a new context so you encounter it naturally.

10. She builds each concept as a chain where the output of one step is the input of the next. "Calcium binds to troponin → troponin changes shape → tropomyosin moves → binding site exposed → myosin attaches → cross bridge forms." No gaps in the chain.

11. She uses analogies sparingly — only for the hardest mechanisms. One or two per entire transcript. She doesn't waste analogies on easy categorisations. Simple content gets trusted prose; complex mechanisms get one well-chosen analogy.

12. She trusts the student's intelligence. She never over-explains simple categorisations. A classification list gets clean flowing prose or a table — no hook, no analogy, no "imagine this." The entertainment is reserved for concepts where the brain genuinely needs help building a mental model.

13. She connects backwards to previous knowledge. "Can you recall the different layers of connective tissue...?" These aren't reminders — they're confidence signals.

14. She writes as if sitting next to the student, watching their face. When their eyes glaze → zoom out. When they lean in → go deep. When they nod → move on fast.

15. She never introduces a structure without placing it physically first. "The sarcoplasmic reticulum, shown here in blue, is an elaborate tubular network that surrounds each myofibril within a muscle fibre." Location before function.

16. She teaches the student HOW to learn, not just WHAT to learn. "A nice approach to learning the terminology is learning the macroscopic structures through to the small, microscopic structures."

17. She uses "let's" to signal gear shifts. "Let's look at," "Let's discuss." It maintains "we're doing this together" and gives the reader's brain a micro-reset.

18. She front-loads exam-relevant detail into the explanation — not as separate tips. The testable fact is indistinguishable from the explanation because understanding IS exam preparation.

19. She uses contrast to teach, not just to categorise. "It only takes 1-2 milliseconds to generate an action potential. However, it takes 20-200 milliseconds to generate a muscle contraction." The contrast teaches you something — electrical is instant, mechanical is slow.

20. She ends sections with forward momentum, not summaries. Zero conclusions. Every section ends by opening the door to the next one.

21. She repeats the hardest concept through different lenses without you noticing. Four passes at the same concept, each adding depth. It never feels repetitive because each pass has a different purpose.

22. She's comfortable with incomplete explanations that get completed later. She plants seeds and trusts they'll be answered. This creates low-level tension that keeps the reader moving.

23. Zero meta-commentary. She never says "this is important" or "this is complex." She just explains it well and trusts you to recognise importance from the depth she gives it.

24. No emotional labour. She never says "don't worry, this gets easier." She doesn't acknowledge difficulty — she just makes it not difficult through clear explanation.

25. No redundant transitions. She never says "now that we've covered X, let's move to Y." She just moves to Y. The structure makes the transition obvious.

26. She teaches vocabulary through nesting, not listing. Each new term is defined as a component of the previous term. The vocabulary builds like Russian nesting dolls, not a flat list.

27. She uses the slide as a co-teacher, not an illustration. She directs your eyes around the diagram and uses spatial position to teach structure. The slide carries half the teaching load.

28. She builds understanding through progressive resolution — like focusing a camera. A concept appears first as a brief mention, then gets its own section, then a detailed walkthrough. Each pass adds resolution. She never tries to explain everything in one shot.

29. She asks questions she knows you can answer. "Can you recall the different layers...?" This activates prior knowledge so new content has something to attach to.

30. She treats the student as a future professional, not a struggling learner. Clinical, professional language — she's modelling how a professional thinks, not dumbing it down.

31. Her paragraph length matches concept density. Simple categorisation = one dense paragraph. Complex mechanism = multiple short paragraphs, one idea each.

32. She uses semicolons and dashes as logical connectors within sentences. One sentence packages three comparison dimensions using parallel structure.

33. She buries corrections inside the flow. She states the correct version as if it's obvious, without announcing "common misconception alert!"

34. She genuinely finds the content beautiful. Her descriptions feel like "let me show you what I see" not "let me dumb this down for you."

35. She writes for the re-reader, not just the first-time reader. A student scanning before an exam can find "Step 2: calcium ions are released" instantly. Clean structure over narrative immersion.

36. She varies sentence length deliberately. Long explanatory sentence followed by short punchy statement. The short sentence lands like a conclusion.

37. She controls the pace of new terminology — at most two new terms per paragraph. When a paragraph needs three, she connects the third to one of the first two.

38. She never explains the evolutionary "why" or the history of discovery. Those are fascinating but not testable.

39. She never qualifies with "it's more complicated than this." She presents a complete picture at the appropriate resolution and leaves it feeling complete.

40. She tells you when you already know something. "As you did at the very beginning of Module 2..." This reduces cognitive anxiety before new content.

41. She gives you answer frameworks, not just answers. "The differences can be characterised by: body location, control mechanism, and mechanism of contraction." Now you have a structure for exam answers.

42. She front-loads the subject in sentences about mechanisms. "Calcium ions are released." "The action potential propagates." The actor comes first, then the action.

43. She uses active voice for mechanisms and passive voice for states. "Calcium floods in" (active — something happening) vs "The thin filaments are composed of actin" (passive — structural description). The voice shift signals whether you're learning a structure or a process.

44. She matches verb intensity to process speed. "Calcium floods in" for fast processes. "Tropomyosin spirals around the actin filaments to stabilise it" for slow ones. The verbs teach timescale.

45. She ends the transcript mid-flow. No conclusion paragraph. Conclusions are for essays, not tutoring. You stop when you're done.

--- FORMATTING ---

The anatomy professor covers muscle contraction — motor units, contraction types, ATP metabolism, fibre types — in about 2,200 words. That's the density to aim for. Most students won't read more than 15 minutes of content, so every word has to earn its place.

For comparisons and categorisations (CNS vs PNS, types of glia, structural neuron classes, virus families), a clean markdown table communicates what three paragraphs of narrative cannot. Use tables. Keep cells terse — 5 to 15 words each. After the table, add one or two sentences highlighting the most exam-relevant pattern. For the 2-3 hardest items in the table, add a brief narrative paragraph below explaining the mechanism.

For mechanisms and processes (action potentials, cross-bridge cycles, synaptic transmission), that's where the full narrative treatment shines. Question-answer chains, precise step numbering, one well-chosen analogy for the hardest part. This is where you spend your words.

For simple definitions and naming conventions, one bold term plus one sentence. Done. Move on.

Use ### sub-headings with a single relevant emoji (e.g., "### 🧬 The Golden Rule"). Bold key terms on first use only. Short paragraphs — 2-4 sentences. Numbered lists only for genuinely sequential steps.

If the concept group metadata says action="skip", write one skip line:
**Topic Name (CI% N%)** — brief reason. Skip.

Within sections you're generating, trim ruthlessly. History-of-discovery stories, professor repeating the same point three ways, tangential examples — cut them or condense to one sentence. Ask: "If I only had 1 hour per week with this student, would I spend time on this?"

--- NON-NEGOTIABLE CONTRACT TERMS ---

These are factual constraints, not style opinions.

Accuracy: You have Google Search. When stating a specific fact (mechanism step, classification detail, organism-disease link), verify it. Prioritise NIH, PubMed, NCBI, university textbooks. If the student's prompt includes a TEXTBOOK REFERENCE section, use it as the primary source for facts. Textbook wins on facts; professor wins on scope.

Exact terminology: "Transcribe" and "translate" are different things in biology. Use the precise term. Don't conflate similar concepts. Verify step order in multi-step processes before writing.

Exam vocabulary: Every described mechanism must name its scientific term, bolded on first use. If you describe "the cell shrinks and breaks into fragments" without writing **apoptosis**, that's a bug. The student will be tested on vocabulary.

Transcript quality: The transcript is auto-captioned garbage — full of misspellings and phonetic manglings ("hippo campus" → hippocampus, "ace tyl co lean" → acetylcholine). Always use correct scientific spelling.

Colloquial precision: Stay casual ("steal" not "takes a portion," "hijack" not "commandeer," contractions always) but never sacrifice scientific accuracy for informality. The scientific term appears; the sentence around it stays conversational.'''


# ---------------------------------------------------------------------------
# Student context — set by pipeline when user profile is available
# ---------------------------------------------------------------------------

_STUDENT_CONTEXT = ""


def set_student_context(program: str = "", year: str = ""):
    """Set the student's context from their quiz answers.

    This adjusts the system prompt to match their assumed knowledge level.
    """
    global _STUDENT_CONTEXT
    parts = []
    if year and program:
        parts.append(f"This student is a {year} {program} student.")
    elif year:
        parts.append(f"This student is in their {year}.")
    elif program:
        parts.append(f"This student is studying {program}.")

    if year:
        y = year.lower()
        if "1st" in y:
            parts.append("Assume NO prior knowledge — build every concept from scratch.")
        elif "2nd" in y:
            parts.append("Assume basic biology knowledge (cell structure, DNA/RNA, basic biochemistry). Skip foundational explanations but still introduce new mechanisms from scratch.")
        elif "3rd" in y:
            parts.append("Assume solid foundational knowledge. Focus on mechanisms, clinical relevance, and exam-specific detail. Skip basic definitions.")
        elif "4th" in y:
            parts.append("Advanced student. Focus on clinical applications, differential diagnosis, and high-yield exam detail. Be concise.")

    _STUDENT_CONTEXT = " ".join(parts)


def get_creative_brief() -> str:
    """Return CREATIVE_BRIEF with student context appended if available."""
    if _STUDENT_CONTEXT:
        return CREATIVE_BRIEF + f"\n\n--- STUDENT ---\n\n{_STUDENT_CONTEXT}"
    return CREATIVE_BRIEF


# ---------------------------------------------------------------------------
# Chunk classification
# ---------------------------------------------------------------------------

# General-purpose patterns for detecting housekeeping and overview chunks
# These match across any lecture, not just microbiology
_SKIP_PATTERNS = re.compile(
    r"housekeeping|introduction\s*/\s*housekeeping|admin|assessment\s+timeline",
    re.IGNORECASE,
)
_MINIMAL_PATTERNS = re.compile(
    r"course\s+overview|module\s+overview|lecture\s+overview|readings?\s+and\s+resources",
    re.IGNORECASE,
)

# Word count targets: (emphasis_score, needs_expansion) -> (min, max)
# These are fallbacks when CI% is not available
WORD_TARGETS = {
    ("HIGH", True): (800, 1200),
    ("HIGH", False): (500, 800),
    ("MEDIUM", True): (600, 900),
    ("MEDIUM", False): (400, 600),
    ("LOW", True): (400, 600),
    ("LOW", False): (200, 400),
}


def ci_word_targets(ci_percent: int, needs_expansion: bool) -> tuple[int, int]:
    """Calculate word count targets from CI% score.

    Calibrated against the anatomy professor — she covers muscle contraction
    (motor units, contraction types, ATP metabolism, fibre types) in ~2,200 words.
    """
    if needs_expansion:
        if ci_percent >= 70:
            return (300, 500)
        elif ci_percent >= 40:
            return (200, 400)
        else:
            return (150, 300)
    else:
        if ci_percent >= 80:
            return (200, 350)
        elif ci_percent >= 60:
            return (150, 250)
        elif ci_percent >= 40:
            return (100, 200)
        else:
            return (50, 120)


def classify_chunk(chunk: Chunk) -> str:
    """Classify a chunk as 'skip', 'minimal', 'expansion', or 'standard'.

    Uses pattern matching, not hardcoded topic names — works for any lecture.
    """
    if _SKIP_PATTERNS.search(chunk.topic_name):
        return "skip"
    if _MINIMAL_PATTERNS.search(chunk.topic_name):
        return "minimal"
    if chunk.needs_expansion:
        return "expansion"
    return "standard"


# ---------------------------------------------------------------------------
# Emphasis resolution (deterministic — no LLM call)
# ---------------------------------------------------------------------------

def resolve_emphasis(signals: list[dict], topic_name: str) -> str:
    """Resolve emphasis signals into a clear 1-2 sentence learning directive.

    Handles contradictory signals (professor says both "important" and "don't memorize").
    """
    if not signals:
        return ""

    has_positive = any(s.get("sentiment") == "positive" for s in signals)
    has_negative = any(s.get("sentiment") == "negative" for s in signals)

    if has_positive and has_negative:
        # Contradictory — the most common case for this bad professor
        return (
            "The professor emphasized this is important to understand conceptually, "
            "but said not to memorize every detail. Translation: understand the underlying "
            "logic and reasoning deeply. If you can explain WHY and HOW, you're good — "
            "you don't need to memorize every specific name or number."
        )
    elif has_positive:
        # Extract what the professor specifically flagged
        keywords = [s.get("keyword", "") for s in signals if s.get("sentiment") == "positive"]
        if any("exam" in k.lower() for k in keywords):
            return "The professor flagged this as exam-relevant. Make sure you understand this thoroughly."
        return "The professor emphasized this topic is important. Focus on understanding it well."
    elif has_negative:
        return (
            "The professor indicated you don't need deep detail here. "
            "Focus on understanding the general concept rather than memorizing specifics."
        )

    return ""


# ---------------------------------------------------------------------------
# Quiz content detection
# ---------------------------------------------------------------------------

def detect_quiz_content(transcript: str) -> tuple[str, str | None]:
    """Split transcript into teaching content and quiz/review content.

    Returns (teaching_content, quiz_content_or_none).
    """
    # Common patterns where professor transitions to quiz review
    quiz_markers = [
        r"(?i)question\s+one\b",
        r"(?i)question\s+1\b",
        r"(?i)multiple\s+choice\s+questions?\s+you\s+can",
        r"(?i)let'?s?\s+see\s+if\s+you\s+can\s+answer",
        r"(?i)just\s+a\s+few\s+multiple\s+choice",
    ]

    for pattern in quiz_markers:
        match = re.search(pattern, transcript)
        if match:
            # Look back a bit for a natural sentence boundary
            split_pos = match.start()
            # Find the last period before the match
            last_period = transcript.rfind(".", 0, split_pos)
            if last_period > split_pos - 200:  # reasonable lookback
                split_pos = last_period + 1

            teaching = transcript[:split_pos].strip()
            quiz = transcript[split_pos:].strip()
            if len(teaching) > 100:  # sanity check
                return teaching, quiz

    return transcript, None


# ---------------------------------------------------------------------------
# Expansion instructions (per-chunk)
# ---------------------------------------------------------------------------

def get_expansion_block(chunk: Chunk) -> str:
    """Get expansion instructions for a chunk, if applicable.

    General-purpose: uses the chunk's own expansion_hint metadata rather than
    hardcoded per-topic instructions. The concept grouper and Stage 1 chunker
    set expansion_hint based on detecting skimmed complex topics.
    """
    if not chunk.needs_expansion:
        return ""
    return (
        f"EXPANSION REQUIRED: {chunk.expansion_hint or 'This topic needs more depth than the professor gave.'}\n"
        "Group similar concepts together rather than treating each one separately. "
        "Spend proportionally more words on harder concepts. "
        "If the professor listed N items in a rush (e.g., 7 classification classes, 5 types), "
        "group them into logical clusters and explain each cluster with its own ### sub-heading."
    )


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def build_user_prompt(chunk: Chunk, prior_topics: list[str],
                      ci_score: CIScore | None = None,
                      screenshots: list[Screenshot] | None = None) -> str:
    """Assemble the per-chunk user prompt."""
    sections = []

    # Header
    sections.append(f"TOPIC: {chunk.topic_name}")
    sections.append(f"EMPHASIS LEVEL: {chunk.emphasis_score}")

    # CI% — curriculum importance (drives depth)
    if ci_score:
        sections.append(
            f"EXAM IMPORTANCE (CI%): {ci_score.ci_percent}% — {ci_score.ci_reasoning}\n"
            f"DEPTH: {ci_score.depth_recommendation.upper()} "
            f"({'Go deep — this is core curriculum.' if ci_score.depth_recommendation == 'deep' else 'Standard depth.' if ci_score.depth_recommendation == 'standard' else 'Keep it light — low exam relevance.'})"
        )

    # Learning guidance
    signals = [s.model_dump() for s in chunk.emphasis_signals]
    guidance = resolve_emphasis(signals, chunk.topic_name)
    if guidance:
        sections.append(f"LEARNING GUIDANCE: {guidance}")

    # Prerequisites
    if chunk.prerequisites and prior_topics:
        prereq_str = ", ".join(chunk.prerequisites[:10])  # cap at 10
        sections.append(
            f"PREREQUISITE CONCEPTS (already explained in earlier sections): {prereq_str}\n"
            "Reference these naturally when relevant — don't re-define them from scratch, "
            "but a brief reminder phrase is fine."
        )

    # Forward references
    if chunk.forward_references:
        fwd_str = ", ".join(chunk.forward_references)
        sections.append(
            f"UPCOMING TOPICS (mentioned here but explained in later sections): {fwd_str}\n"
            "If the professor references these, briefly note they'll be covered later."
        )

    # Expansion block
    expansion = get_expansion_block(chunk)
    if expansion:
        sections.append(expansion)

    # Transcript
    # Strip quiz content if present
    teaching_text, quiz_text = detect_quiz_content(chunk.transcript_text)
    sections.append(
        f'RAW TRANSCRIPT (professor\'s rambling — use as source material for WHAT to teach, not HOW):\n"""\n{teaching_text}\n"""'
    )
    if quiz_text:
        sections.append("(Quiz review content was stripped from the transcript above.)")

    # Key terms
    # Filter out noise terms (multi-word phrases that aren't real terms)
    real_terms = [t for t in chunk.key_terms if len(t.split()) <= 4 and not t.startswith("so ") and not t.startswith("but ") and not t.startswith("although ")]
    if real_terms:
        sections.append(f"KEY TERMS TO COVER: {', '.join(real_terms[:15])}")

    # Lecture screenshots
    if screenshots:
        screenshot_lines = []
        for ss in screenshots:
            screenshot_lines.append(f"- [{ss.timestamp_display}] {ss.description} ({ss.image_filename})")
        sections.append(
            "LECTURE SCREENSHOTS (from the video at these timestamps):\n"
            + "\n".join(screenshot_lines) + "\n"
            "Reference these naturally in your explanation where relevant, e.g.: "
            "\"As shown in the lecture slide at 12:34, the structure looks like...\" "
            "These give the student visual anchors to the actual lecture materials."
        )

    # Word count guidance — CI%-driven if available, fallback to emphasis-based
    if ci_score:
        min_words, max_words = ci_word_targets(ci_score.ci_percent, chunk.needs_expansion)
    else:
        wt_key = (chunk.emphasis_score, chunk.needs_expansion)
        min_words, max_words = WORD_TARGETS.get(wt_key, (400, 600))
    sections.append(
        f"Aim for {min_words}-{max_words} words. The anatomy professor covers motor units, contraction types, "
        "ATP metabolism, and fibre types in ~2,200 words total. Match that density."
    )

    # Final instruction
    sections.append(
        "Generate a tutor-quality explanation that REPLACES this section of the lecture. "
        "The student will read YOUR explanation instead of watching this part. Make it count."
    )

    return "\n\n".join(sections)


def build_slide_prompt(slide: "SlideChunk", prior_topics: list[str],
                       ci_score: CIScore | None = None) -> str:
    """Assemble the prompt for a slide-based chunk."""
    from src.models import SlideChunk
    sections = []

    # Slide header
    sections.append(f"SLIDE: Slide {slide.slide_index} ({slide.timestamp_display})")
    sections.append(f"SLIDE VISUAL: {slide.slide_description}")

    # CI%
    if ci_score:
        sections.append(
            f"EXAM IMPORTANCE (CI%): {ci_score.ci_percent}% — {ci_score.ci_reasoning}\n"
            f"DEPTH: {ci_score.depth_recommendation.upper()} "
            f"({'Go deep — this is core curriculum.' if ci_score.depth_recommendation == 'deep' else 'Standard depth.' if ci_score.depth_recommendation == 'standard' else 'Keep it light — low exam relevance.'})"
        )

    # Learning guidance
    signals = [s.model_dump() for s in slide.emphasis_signals]
    guidance = resolve_emphasis(signals, slide.topic_name)
    if guidance:
        sections.append(f"LEARNING GUIDANCE: {guidance}")

    # Prior slides
    if prior_topics:
        sections.append(
            f"PREVIOUS SLIDES COVERED: {', '.join(prior_topics[-5:])}\n"
            "Reference earlier content naturally — don't re-explain concepts already covered."
        )

    # Transcript
    teaching_text, quiz_text = detect_quiz_content(slide.transcript_text)
    sections.append(
        f'RAW TRANSCRIPT (professor\'s words during this slide):\n"""\n{teaching_text}\n"""'
    )
    if quiz_text:
        sections.append("(Quiz review content was stripped.)")

    # Key terms
    real_terms = [t for t in slide.key_terms if len(t.split()) <= 4
                  and not t.startswith("so ") and not t.startswith("but ")]
    if real_terms:
        sections.append(f"KEY TERMS TO COVER: {', '.join(real_terms[:15])}")

    # Sub-chunking guidance
    if slide.needs_sub_chunking:
        sections.append(
            "NOTE: This slide covers a lot of content. Use ### sub-headings to organize "
            "the explanation into logical sub-topics within this slide section."
        )

    # Word count
    if ci_score:
        min_words, max_words = ci_word_targets(ci_score.ci_percent, slide.needs_sub_chunking)
    else:
        wt_key = (slide.emphasis_score, slide.needs_sub_chunking)
        min_words, max_words = WORD_TARGETS.get(wt_key, (400, 600))
    sections.append(
        f"Aim for {min_words}-{max_words} words. Match the anatomy professor's density."
    )

    # Slide reference instruction
    sections.append(
        f"The student has a companion slide deck. Reference this slide naturally: "
        f"\"Looking at Slide {slide.slide_index}, you can see...\"\n"
        "Generate a tutor-quality explanation for this slide's content."
    )

    return "\n\n".join(sections)


def build_minimal_prompt(chunk: Chunk) -> str:
    """Build a simple prompt for orientation/overview chunks."""
    return (
        f"Write a 2-3 sentence orientation note for a student about to study this module.\n"
        f"Based on this transcript excerpt, summarize what the module covers and any "
        f"key textbook references mentioned. Keep it factual and brief.\n\n"
        f'TRANSCRIPT:\n"""\n{chunk.transcript_text[:1000]}\n"""'
    )


# ---------------------------------------------------------------------------
# Vertex AI LLM call
# ---------------------------------------------------------------------------

def call_llm(user_prompt: str, system_prompt: str = CREATIVE_BRIEF,
             temperature: float = 0.7, max_tokens: int = 8192,
             use_search: bool = True) -> str:
    """Call Gemini via Vertex AI and return the response text.

    Args:
        use_search: If True, enable Google Search grounding so the model
                    can verify facts while generating. This prevents hallucinations
                    at the source rather than catching them after.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)

    config = {
        "system_instruction": system_prompt,
        "temperature": temperature,
        "max_output_tokens": max_tokens,
    }

    # Enable Google Search grounding for factual accuracy during generation
    if use_search:
        config["tools"] = [types.Tool(google_search=types.GoogleSearch())]

    response = client.models.generate_content(
        model=GENERATOR_MODEL,
        contents=user_prompt,
        config=config,
    )
    return (response.text or "").strip()


def call_llm_with_retry(user_prompt: str, system_prompt: str = CREATIVE_BRIEF,
                        temperature: float = 0.7, max_tokens: int = 8192,
                        retries: int = 2) -> str:
    """Call LLM with retry on transient errors."""
    for attempt in range(retries + 1):
        try:
            return call_llm(user_prompt, system_prompt, temperature, max_tokens)
        except Exception as e:
            error_str = str(e)
            if attempt < retries and any(code in error_str for code in ["429", "500", "503", "RESOURCE_EXHAUSTED"]):
                wait = 5 * (attempt + 1)
                print(f"  Retrying in {wait}s (attempt {attempt + 1}/{retries})... Error: {error_str[:100]}")
                time.sleep(wait)
            else:
                raise


# ---------------------------------------------------------------------------
# Core generation
# ---------------------------------------------------------------------------

def generate_explanation(chunk: Chunk, prior_topics: list[str],
                         ci_score: CIScore | None = None,
                         screenshots: list[Screenshot] | None = None) -> Explanation:
    """Generate explanation for a single chunk."""
    chunk_type = classify_chunk(chunk)
    now = datetime.now(timezone.utc).isoformat()

    # Skip housekeeping
    if chunk_type == "skip":
        return Explanation(
            chunk_index=chunk.chunk_index,
            topic_name=chunk.topic_name,
            explanation_text="",
            word_count=0,
            emphasis_score=chunk.emphasis_score,
            learning_guidance="",
            was_skipped=True,
            skip_reason="Housekeeping — assessment timelines, no teaching content",
            generation_model=GENERATOR_MODEL,
            generation_timestamp=now,
        )

    # Minimal orientation
    if chunk_type == "minimal":
        prompt = build_minimal_prompt(chunk)
        try:
            text = call_llm_with_retry(
                prompt,
                system_prompt="Write a brief, factual orientation note for a university student.",
                temperature=0.3,
                max_tokens=512,
            )
        except Exception as e:
            text = f"[GENERATION FAILED — chunk {chunk.chunk_index}: {e}]"

        return Explanation(
            chunk_index=chunk.chunk_index,
            topic_name=chunk.topic_name,
            explanation_text=text,
            word_count=len(text.split()),
            emphasis_score=chunk.emphasis_score,
            learning_guidance="",
            generation_model=GENERATOR_MODEL,
            generation_timestamp=now,
        )

    # Standard or expansion
    prompt = build_user_prompt(chunk, prior_topics, ci_score=ci_score, screenshots=screenshots)

    signals = [s.model_dump() for s in chunk.emphasis_signals]
    guidance = resolve_emphasis(signals, chunk.topic_name)

    try:
        text = call_llm_with_retry(prompt, max_tokens=8192)
    except Exception as e:
        text = f"[GENERATION FAILED — chunk {chunk.chunk_index}: {e}]"

    # Extract which key terms were actually mentioned in the output
    real_terms = [t for t in chunk.key_terms if len(t.split()) <= 4
                  and not t.startswith("so ") and not t.startswith("but ")]
    terms_explained = [t for t in real_terms if t.lower() in text.lower()]

    return Explanation(
        chunk_index=chunk.chunk_index,
        topic_name=chunk.topic_name,
        explanation_text=text,
        word_count=len(text.split()),
        emphasis_score=chunk.emphasis_score,
        learning_guidance=guidance,
        key_terms_explained=terms_explained,
        prerequisites_referenced=chunk.prerequisites[:10],
        ci_percent=ci_score.ci_percent if ci_score else None,
        ci_reasoning=ci_score.ci_reasoning if ci_score else "",
        screenshot_refs=[s.image_filename for s in screenshots] if screenshots else [],
        was_expanded=chunk.needs_expansion,
        generation_model=GENERATOR_MODEL,
        generation_timestamp=now,
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_all(
    chunks_path: str,
    output_path: str | None = None,
    chunk_indices: list[int] | None = None,
    dry_run: bool = False,
    ci_scores_path: str | None = None,
    screenshots_path: str | None = None,
) -> list[Explanation]:
    """Process all chunks and generate explanations.

    Args:
        chunks_path: path to Stage 1 chunks JSON
        output_path: where to save output (auto-generated if None)
        chunk_indices: if provided, only process these chunk indices
        dry_run: if True, print prompts without making LLM calls
        ci_scores_path: path to CI scores JSON (from Stage 1.5a)
        screenshots_path: path to screenshots JSON (from Stage 1.5b)
    """
    # Load chunks
    with open(chunks_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    chunks = [Chunk(**c) for c in raw]
    print(f"Loaded {len(chunks)} chunks from {chunks_path}")

    # Load CI scores if available
    ci_scores_map: dict[int, CIScore] = {}
    if ci_scores_path:
        try:
            with open(ci_scores_path, "r", encoding="utf-8") as f:
                ci_raw = json.load(f)
            for cs in ci_raw:
                ci_scores_map[cs["chunk_index"]] = CIScore(**cs)
            print(f"Loaded {len(ci_scores_map)} CI scores from {ci_scores_path}")
        except Exception as e:
            print(f"Warning: Could not load CI scores: {e}")

    # Load screenshots if available
    screenshots_map: dict[int, list[Screenshot]] = {}
    if screenshots_path:
        try:
            with open(screenshots_path, "r", encoding="utf-8") as f:
                ss_raw = json.load(f)
            for ss in ss_raw:
                idx = ss["matched_chunk_index"]
                if idx not in screenshots_map:
                    screenshots_map[idx] = []
                screenshots_map[idx].append(Screenshot(**ss))
            total_ss = sum(len(v) for v in screenshots_map.values())
            print(f"Loaded {total_ss} screenshots across {len(screenshots_map)} chunks from {screenshots_path}")
        except Exception as e:
            print(f"Warning: Could not load screenshots: {e}")

    if chunk_indices is not None:
        target_indices = set(chunk_indices)
        print(f"Processing only chunks: {sorted(target_indices)}")
    else:
        target_indices = None

    explanations = []
    prior_topics: list[str] = []

    for i, chunk in enumerate(chunks):
        # Skip if not in target set (but still track prior_topics)
        if target_indices is not None and chunk.chunk_index not in target_indices:
            prior_topics.append(chunk.topic_name)
            continue

        chunk_type = classify_chunk(chunk)
        tag = ""
        if chunk_type == "skip":
            tag = " (housekeeping)"
        elif chunk_type == "minimal":
            tag = " (orientation)"
        elif chunk_type == "expansion":
            tag = " [EXPANSION]"

        label = f"[{i + 1}/{len(chunks)}]"

        if chunk_type == "skip":
            print(f"{label} SKIP: {chunk.topic_name}{tag}")
        else:
            print(f"{label} {chunk.topic_name}{tag}")

        # Get CI score and screenshots for this chunk
        chunk_ci = ci_scores_map.get(chunk.chunk_index)
        chunk_screenshots = screenshots_map.get(chunk.chunk_index, [])

        if dry_run:
            # Print the prompt instead of calling LLM
            if chunk_type == "skip":
                print("  → Skipped (no prompt generated)\n")
            elif chunk_type == "minimal":
                print(f"  → Prompt:\n{build_minimal_prompt(chunk)}\n")
            else:
                prompt = build_user_prompt(chunk, prior_topics,
                                          ci_score=chunk_ci,
                                          screenshots=chunk_screenshots or None)
                print(f"  → Prompt ({len(prompt)} chars):\n{prompt}\n")
                print("-" * 80)
            prior_topics.append(chunk.topic_name)
            continue

        # Generate
        explanation = generate_explanation(chunk, prior_topics,
                                          ci_score=chunk_ci,
                                          screenshots=chunk_screenshots or None)
        explanations.append(explanation)

        if not explanation.was_skipped:
            _, quiz = detect_quiz_content(chunk.transcript_text)
            quiz_note = ""
            if quiz:
                pct = len(quiz) * 100 // len(chunk.transcript_text)
                quiz_note = f" (quiz content stripped: {pct}% of transcript)"
            print(f"  → {explanation.word_count} words{quiz_note}")

        prior_topics.append(chunk.topic_name)

        # Intermediate save
        if output_path:
            _save_explanations(explanations, output_path)

    # Final save
    if not dry_run and explanations:
        if output_path is None:
            from pathlib import Path
            stem = Path(chunks_path).stem
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            output_path = str(Path(chunks_path).parent / f"{stem}_{ts}_explanations.json")

        _save_explanations(explanations, output_path)
        total_words = sum(e.word_count for e in explanations)
        skipped = sum(1 for e in explanations if e.was_skipped)
        expanded = sum(1 for e in explanations if e.was_expanded)
        print(f"\nDone. {len(explanations)} explanations saved to {output_path}")
        print(f"  Total words: {total_words:,} | Skipped: {skipped} | Expanded: {expanded}")

    return explanations


def generate_from_slides(
    slide_chunks_path: str,
    output_path: str | None = None,
    ci_scores_path: str | None = None,
    dry_run: bool = False,
) -> list[Explanation]:
    """Generate explanations from slide-based chunks.

    This is the slide-based equivalent of generate_all().
    """
    from src.models import SlideChunk

    # Load slide chunks
    with open(slide_chunks_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    slides = [SlideChunk(**s) for s in raw]
    print(f"Loaded {len(slides)} slide chunks from {slide_chunks_path}")

    # Load CI scores
    ci_scores_map: dict[int, CIScore] = {}
    if ci_scores_path:
        try:
            with open(ci_scores_path, "r", encoding="utf-8") as f:
                ci_raw = json.load(f)
            for cs in ci_raw:
                ci_scores_map[cs["chunk_index"]] = CIScore(**cs)
            print(f"Loaded {len(ci_scores_map)} CI scores")
        except Exception as e:
            print(f"Warning: Could not load CI scores: {e}")

    explanations = []
    prior_topics: list[str] = []
    now = datetime.now(timezone.utc).isoformat()

    for i, slide in enumerate(slides):
        label = f"[{i + 1}/{len(slides)}]"

        # Skip housekeeping slides (first slide if it's admin/intro)
        is_housekeeping = (slide.slide_index == 1 and slide.word_count > 1500
                          and any(w in slide.transcript_text.lower()[:500]
                                  for w in ["assessment", "workshop", "module one", "revision"]))

        if is_housekeeping:
            print(f"{label} SKIP: Slide {slide.slide_index} (housekeeping)")
            explanations.append(Explanation(
                chunk_index=slide.slide_index,
                topic_name=f"Slide {slide.slide_index} — Housekeeping",
                explanation_text="",
                word_count=0,
                emphasis_score=slide.emphasis_score,
                learning_guidance="",
                was_skipped=True,
                skip_reason="Housekeeping / admin content",
                generation_model=GENERATOR_MODEL,
                generation_timestamp=now,
            ))
            prior_topics.append("Housekeeping")
            continue

        # Get CI score (map by slide index)
        ci_score = ci_scores_map.get(slide.slide_index)

        sub_tag = " [SUB-CHUNK]" if slide.needs_sub_chunking else ""
        print(f"{label} Slide {slide.slide_index} — {slide.topic_name[:40]}{sub_tag}")

        if dry_run:
            prompt = build_slide_prompt(slide, prior_topics, ci_score=ci_score)
            print(f"  → Prompt ({len(prompt)} chars):\n{prompt}\n")
            print("-" * 80)
            prior_topics.append(slide.topic_name)
            continue

        # Generate
        prompt = build_slide_prompt(slide, prior_topics, ci_score=ci_score)
        signals = [s.model_dump() for s in slide.emphasis_signals]
        guidance = resolve_emphasis(signals, slide.topic_name)

        try:
            text = call_llm_with_retry(prompt, max_tokens=8192)
        except Exception as e:
            text = f"[GENERATION FAILED — slide {slide.slide_index}: {e}]"

        explanation = Explanation(
            chunk_index=slide.slide_index,
            topic_name=f"Slide {slide.slide_index} — {slide.topic_name[:50]}",
            explanation_text=text,
            word_count=len(text.split()),
            emphasis_score=slide.emphasis_score,
            learning_guidance=guidance,
            key_terms_explained=[t for t in slide.key_terms if t.lower() in text.lower()],
            ci_percent=ci_score.ci_percent if ci_score else None,
            ci_reasoning=ci_score.ci_reasoning if ci_score else "",
            screenshot_refs=[slide.slide_image],
            was_expanded=slide.needs_sub_chunking,
            generation_model=GENERATOR_MODEL,
            generation_timestamp=now,
        )
        explanations.append(explanation)
        print(f"  → {explanation.word_count} words")
        prior_topics.append(slide.topic_name)

        # Intermediate save
        if output_path:
            _save_explanations(explanations, output_path)

    # Final save
    if not dry_run and explanations:
        if output_path is None:
            from pathlib import Path
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            output_path = f"data/output/slide_explanations_{ts}.json"
        _save_explanations(explanations, output_path)
        total_words = sum(e.word_count for e in explanations)
        skipped = sum(1 for e in explanations if e.was_skipped)
        print(f"\nDone. {len(explanations)} explanations saved to {output_path}")
        print(f"  Total words: {total_words:,} | Skipped: {skipped}")

    return explanations


def _save_explanations(explanations: list[Explanation], path: str):
    """Save explanations to JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump([e.model_dump() for e in explanations], f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# V4: Concept Group generation
# ---------------------------------------------------------------------------

def build_group_prompt(group, prior_group_names: list[str],
                       textbook_context: str | None = None) -> str:
    """Build a prompt for a ConceptGroup (v4 pipeline).

    Args:
        group: ConceptGroup dataclass instance
        prior_group_names: names of groups already generated (for continuity)
        textbook_context: relevant textbook chapter text (if available)
    """
    from src.concept_grouper import ConceptGroup

    sections = []

    # Header
    sections.append(f"CONCEPT GROUP: {group.group_name}")
    sections.append(f"EXAM IMPORTANCE (CI%): {group.ci_percent}%")
    sections.append(f"EMPHASIS: {group.emphasis_score}")

    # Action context
    if group.needs_expansion:
        hints = "\n".join(f"  - {h}" for h in group.expansion_hints) if group.expansion_hints else ""
        sections.append(
            f"ACTION: EXPAND — the professor skimmed this but it's important.\n"
            f"Go deep. The student needs this for exams.{chr(10) + hints if hints else ''}"
        )

    # Prior context
    if prior_group_names:
        sections.append(
            f"ALREADY COVERED: {', '.join(prior_group_names[-5:])}\n"
            "Reference earlier content naturally — don't re-explain, but brief reminders are fine."
        )

    # Prerequisites
    if group.prerequisites:
        sections.append(f"PREREQUISITE CONCEPTS: {', '.join(group.prerequisites[:10])}")

    # Key terms — filter transcript garbage using general-purpose detector
    from src.completeness_checker import _is_noise_term
    real_terms = [t for t in group.key_terms if not _is_noise_term(t.lower().strip())]
    if real_terms:
        sections.append(f"KEY TERMS TO COVER: {', '.join(real_terms[:15])}")

    # Textbook reference (primary source of factual truth)
    if textbook_context:
        sections.append(
            "TEXTBOOK REFERENCE (use this as your PRIMARY source for all factual claims):\n"
            "Use the textbook for: mechanisms, sequences, structures, timing, terminology.\n"
            "Use the professor's transcript for: scope (what to emphasise, skip, expand).\n"
            "If the professor states a fact that contradicts the textbook, follow the textbook.\n"
            f'"""\n{textbook_context[:4000]}\n"""'
        )

    # Transcript
    teaching_text, quiz_text = detect_quiz_content(group.raw_transcript)
    sections.append(
        f'RAW TRANSCRIPT (professor\'s words — use for WHAT topics to cover and scope decisions, not as factual source):\n'
        f'"""\n{teaching_text}\n"""'
    )
    if quiz_text:
        sections.append("(Quiz review content was stripped from the transcript above.)")

    # Word budget
    min_words, max_words = ci_word_targets(group.ci_percent, group.needs_expansion)
    sections.append(
        f"Aim for {min_words}-{max_words} words. Match the anatomy professor's density — "
        "she covers an entire topic (motor units, contraction types, ATP pathways, fibre types) in ~2,200 words total."
    )

    # Final instruction
    sections.append(
        "Write an explanation for this concept group that replaces this part of the lecture. "
        "The student reads your output instead of watching the recording. "
        "Group related concepts logically — you don't have to follow the professor's order."
    )

    return "\n\n".join(sections)


def _generate_single_group(args: tuple) -> dict:
    """Generate explanation for a single group. Used by parallel executor.

    Args is a tuple: (group, prior_names, group_index, total_groups, now)
    Returns dict with group_index and result Explanation or None.
    """
    group, prior_names, idx, total, now = args
    from src.fact_checker import fetch_textbook_chapter

    label = f"[{idx + 1}/{total}]"
    tag = " [EXPAND]" if group.needs_expansion else ""
    print(f"{label} {group.group_name}{tag} (CI% {group.ci_percent}%)")

    # Fetch textbook
    textbook = None
    try:
        textbook = fetch_textbook_chapter(group.group_name)
    except Exception as e:
        print(f"  (textbook fetch failed: {e})")

    prompt = build_group_prompt(group, prior_names, textbook_context=textbook)

    try:
        text = call_llm_with_retry(prompt, system_prompt=get_creative_brief(), max_tokens=8192)
    except Exception as e:
        text = f"[GENERATION FAILED — group {group.group_index}: {e}]"

    terms_explained = [t for t in group.key_terms if t.lower() in text.lower()]
    print(f"  → {len(text.split())} words, {len(terms_explained)}/{len(group.key_terms)} terms covered")

    return {
        "group_index": group.group_index,
        "explanation": Explanation(
            chunk_index=group.group_index,
            topic_name=group.group_name,
            explanation_text=text,
            word_count=len(text.split()),
            emphasis_score=group.emphasis_score,
            learning_guidance="",
            key_terms_explained=terms_explained,
            prerequisites_referenced=group.prerequisites[:10],
            ci_percent=group.ci_percent,
            was_expanded=group.needs_expansion,
            generation_model=GENERATOR_MODEL,
            generation_timestamp=now,
        ),
    }


def generate_from_groups(
    groups,
    output_path: str | None = None,
    dry_run: bool = False,
    group_indices: list[int] | None = None,
) -> list[Explanation]:
    """Generate explanations from ConceptGroups (v4 pipeline).

    Uses ThreadPoolExecutor to generate all sections in parallel.
    Textbook fetches + Pro generation happen concurrently (~3x faster).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from src.concept_grouper import ConceptGroup

    target_indices = set(group_indices) if group_indices is not None else None
    now = datetime.now(timezone.utc).isoformat()

    explanations = []
    parallel_tasks = []

    # Pre-compute prior_group_names for each group (since order is fixed)
    all_names = [g.group_name for g in groups]

    for group in groups:
        if target_indices is not None and group.group_index not in target_indices:
            continue

        label = f"[{group.group_index + 1}/{len(groups)}]"

        # Handle skips
        if group.action == "skip":
            print(f"{label} SKIP: {group.group_name}")
            skip_msg = group.skip_message or f"Low priority (CI% {group.ci_percent}%). Skipped."
            explanations.append(Explanation(
                chunk_index=group.group_index,
                topic_name=group.group_name,
                explanation_text=f"**{group.group_name} (CI% {group.ci_percent}%)** — {skip_msg}",
                word_count=len(skip_msg.split()),
                emphasis_score=group.emphasis_score,
                learning_guidance="",
                was_skipped=True,
                skip_reason=skip_msg,
                ci_percent=group.ci_percent,
                generation_model=GENERATOR_MODEL,
                generation_timestamp=now,
            ))
            continue

        # Handle minimal
        if group.action == "minimal":
            print(f"{label} MINIMAL: {group.group_name}")
            if not dry_run:
                prompt = build_minimal_prompt_from_group(group)
                try:
                    text = call_llm_with_retry(
                        prompt,
                        system_prompt="Write a brief, friendly orientation note for a university student.",
                        temperature=0.3,
                        max_tokens=512,
                    )
                except Exception as e:
                    text = f"[GENERATION FAILED — group {group.group_index}: {e}]"
                explanations.append(Explanation(
                    chunk_index=group.group_index,
                    topic_name=group.group_name,
                    explanation_text=text,
                    word_count=len(text.split()),
                    emphasis_score=group.emphasis_score,
                    learning_guidance="",
                    ci_percent=group.ci_percent,
                    generation_model=GENERATOR_MODEL,
                    generation_timestamp=now,
                ))
            continue

        # Queue for parallel generation
        prior_names = all_names[:group.group_index]
        parallel_tasks.append((group, prior_names, group.group_index, len(groups), now))

    # Run all standard/expansion groups in parallel
    if parallel_tasks and not dry_run:
        print(f"\nGenerating {len(parallel_tasks)} sections in parallel...")
        parallel_results = {}
        with ThreadPoolExecutor(max_workers=min(6, len(parallel_tasks))) as executor:
            futures = {executor.submit(_generate_single_group, task): task
                       for task in parallel_tasks}
            for future in as_completed(futures):
                try:
                    result = future.result()
                    parallel_results[result["group_index"]] = result["explanation"]
                except Exception as e:
                    task = futures[future]
                    group = task[0]
                    print(f"  Generation failed for {group.group_name}: {e}")

        # Add parallel results in correct order
        for task in parallel_tasks:
            group = task[0]
            if group.group_index in parallel_results:
                explanations.append(parallel_results[group.group_index])

    elif dry_run:
        for task in parallel_tasks:
            group, prior_names = task[0], task[1]
            prompt = build_group_prompt(group, prior_names)
            print(f"  → Prompt ({len(prompt)} chars):\n{prompt}\n")
            print("-" * 80)

    # Sort explanations by group_index for correct document order
    explanations.sort(key=lambda e: e.chunk_index)

    # Final save
    if not dry_run and explanations:
        if output_path is None:
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            output_path = f"data/output/v4_explanations_{ts}.json"

        _save_explanations(explanations, output_path)
        total_words = sum(e.word_count for e in explanations)
        skipped = sum(1 for e in explanations if e.was_skipped)
        expanded = sum(1 for e in explanations if e.was_expanded)
        print(f"\nDone. {len(explanations)} explanations saved to {output_path}")
        print(f"  Total words: {total_words:,} | Skipped: {skipped} | Expanded: {expanded}")

    return explanations


def build_minimal_prompt_from_group(group) -> str:
    """Build a minimal prompt for orientation/overview groups."""
    return (
        f"Write a 2-3 sentence orientation note for a student about to study this module.\n"
        f"Based on this transcript excerpt, summarize what the module covers and any "
        f"key textbook references mentioned. Keep it factual and brief.\n\n"
        f'TRANSCRIPT:\n"""\n{group.raw_transcript[:1000]}\n"""'
    )
