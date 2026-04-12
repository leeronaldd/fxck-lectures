"""
Stage 1: Token-free transcript chunker.

Splits lecture transcripts into teachable topic chunks using regex-based
marker detection. Falls back to Vertex AI (Gemini Flash) only when no
structural markers are found.
"""

import re
from collections import Counter
from src.models import Chunk, EmphasisSignal


# ---------------------------------------------------------------------------
# Marker detection patterns
# ---------------------------------------------------------------------------

# Explicit slide/topic markers (structured transcripts)
SLIDE_MARKER = re.compile(r'\bSlide\s+(\d+)\b', re.IGNORECASE)
TOPIC_MARKER = re.compile(r'\btopic\s+(\d+)\b', re.IGNORECASE)

# Professor transition phrases (rambling transcripts)
# These signal the professor is moving to a new concept.
TRANSITION_PATTERNS = [
    # Direct topic shifts
    re.compile(r"(?:so\s+)?(?:we\s+)?(?:start|begin)\s+(?:off\s+)?(?:with\s+|our\s+)?(?:the\s+)?(?:first|next|second|third)\s+topic", re.IGNORECASE),
    re.compile(r"(?:let's|let\s+us)\s+(?:have\s+a\s+look\s+at|look\s+at|move\s+on\s+to|talk\s+about|go\s+(?:on\s+)?to)", re.IGNORECASE),
    re.compile(r"(?:okay|so|all\s+right)[,.]?\s+(?:so\s+)?(?:let's\s+)?move\s+on\s+(?:to|then)", re.IGNORECASE),
    re.compile(r"(?:we're\s+going\s+to|we'll)\s+(?:now\s+)?(?:cover|look\s+at|talk\s+about|deal\s+with|go\s+(?:through|into))", re.IGNORECASE),
    re.compile(r"(?:now\s+)?(?:let's|we)\s+(?:now\s+)?(?:extend|turn|shift|move)\s+(?:this\s+)?to", re.IGNORECASE),
    # Section openers with subject name
    re.compile(r"(?:okay|so|all\s+right)[,.]?\s+(?:so\s+)?(?:our|the)\s+(?:next|first|second|last)\s+(?:topic|section|part|thing)", re.IGNORECASE),
    re.compile(r"(?:okay|so)[,.]?\s+(?:so\s+)?(?:back\s+to|onto)\s+", re.IGNORECASE),
    # Concept introductions (professor introducing a system/framework/concept)
    re.compile(r"(?:what's|what\s+is)\s+called\s+(?:the\s+)?(?:\w+\s+){1,3}(?:system|classification|method|process|cycle|theory)", re.IGNORECASE),
    re.compile(r"(?:the\s+way\s+we\s+(?:do\s+)?(?:classify|categorize|group|name|identify))", re.IGNORECASE),
    re.compile(r"(?:is\s+(?:based|classified|grouped|named|called)\s+(?:on|according\s+to)\s+(?:what's\s+called\s+)?(?:the\s+)?)", re.IGNORECASE),
    # Naming/classification section openers
    re.compile(r"\b(?:naming|classification|taxonomy)\s+of\s+", re.IGNORECASE),
    # "So our [CONCEPT]" pattern (e.g., "So our DNA viruses")
    re.compile(r"(?:okay|so)[,.]?\s+(?:so\s+)?our\s+(?:DNA|RNA|class|group|type|lytic|lysogenic|animal|plant|bacterial)", re.IGNORECASE),
    # Overall process descriptions
    re.compile(r"(?:okay|so)[,.]?\s+(?:so\s+)?(?:the\s+)?overall\s+process\s+of", re.IGNORECASE),
]

# Emphasis keywords that signal importance
EMPHASIS_POSITIVE = [
    (re.compile(r"\b(?:that'?s?\s+)?(?:really\s+)?important\b", re.IGNORECASE), "important"),
    (re.compile(r"\bmake\s+sure\s+(?:you\s+)?(?:know|understand|remember)\b", re.IGNORECASE), "make sure you know"),
    (re.compile(r"\bI\s+(?:really\s+)?(?:want|need)\s+you\s+to\s+know\b", re.IGNORECASE), "I want you to know"),
    (re.compile(r"\byou\s+need\s+to\s+know\b", re.IGNORECASE), "you need to know"),
    (re.compile(r"\b(?:key|critical|crucial|essential)\s+(?:point|concept|thing|idea)\b", re.IGNORECASE), "key point"),
    (re.compile(r"\bfor\s+(?:the\s+)?(?:exam|quiz|test|assessment)\b", re.IGNORECASE), "exam relevant"),
    (re.compile(r"\bremember\s+(?:that|this)\b", re.IGNORECASE), "remember"),
    (re.compile(r"\bthat'?s\s+really\b", re.IGNORECASE), "that's really"),
]

EMPHASIS_NEGATIVE = [
    (re.compile(r"\bI\s+don'?t\s+(?:want|need|expect)\s+you\s+to\s+(?:memorize|memorise|know\s+all)\b", re.IGNORECASE), "don't memorize"),
    (re.compile(r"\bnot\s+expecting\s+you\s+to\s+know\b", re.IGNORECASE), "not expecting you to know"),
    (re.compile(r"\bdon'?t\s+(?:worry|stress)\s+(?:about|too\s+much)\b", re.IGNORECASE), "don't worry about"),
    (re.compile(r"\bjust\s+(?:be\s+)?aware\b", re.IGNORECASE), "just be aware"),
    (re.compile(r"\bwe\s+won'?t\s+(?:worry|go\s+into)\b", re.IGNORECASE), "won't worry about"),
]

# Biomedical science technical terms for prerequisite mapping.
# Broad coverage across microbiology, anatomy, physiology, pharmacology, pathology.
# This list bootstraps the term extractor — it also learns terms from context.
SEED_TERMS = {
    # --- General biology / cell biology ---
    "genome", "nucleic acid", "dna", "rna", "mrna", "messenger rna",
    "double stranded", "single stranded", "positive sense", "negative sense",
    "replication", "transcription", "translation", "gene expression",
    "protein", "enzyme", "receptor", "ligand", "substrate", "cofactor",
    "cell membrane", "cytoplasm", "nucleus", "mitochondria", "ribosome",
    "endoplasmic reticulum", "golgi apparatus", "lysosome", "vesicle",
    "atp", "metabolism", "catabolism", "anabolism", "glycolysis", "krebs cycle",
    "oxidative phosphorylation", "electron transport chain",
    # --- Microbiology ---
    "virus", "virion", "capsid", "capsomere", "nucleocapsid", "envelope",
    "spike protein", "glycoprotein", "lipid bilayer", "lipid envelope",
    "bacteriophage", "phage", "lytic", "lysogenic", "prophage", "temperate",
    "host cell", "adsorption", "penetration", "budding", "lysis",
    "baltimore classification", "taxonomy", "classification", "morphology",
    "peptidoglycan", "cell wall", "cytoplasmic membrane",
    "endotoxin", "exotoxin", "gram positive", "gram negative",
    "biofilm", "conjugation", "transduction", "transformation",
    "antibiotic", "antimicrobial", "resistance", "plasmid",
    # --- Anatomy / Physiology ---
    "muscle", "contraction", "isotonic", "isometric", "concentric", "eccentric",
    "bone", "cartilage", "tendon", "ligament", "joint", "synovial",
    "neuron", "synapse", "axon", "dendrite", "neurotransmitter",
    "action potential", "depolarization", "repolarization",
    "cardiac", "vascular", "artery", "vein", "capillary",
    "ventricle", "atrium", "systole", "diastole", "blood pressure",
    "respiratory", "alveoli", "bronchi", "diaphragm", "ventilation",
    "immune system", "antibody", "antigen", "lymphocyte", "phagocyte",
    "inflammation", "cytokine", "complement", "innate", "adaptive",
    # --- Pharmacology ---
    "agonist", "antagonist", "partial agonist", "inverse agonist",
    "dose response", "efficacy", "potency", "therapeutic index",
    "pharmacokinetics", "pharmacodynamics", "half life",
    "absorption", "distribution", "metabolism", "excretion",
    "first pass", "bioavailability", "volume of distribution",
    # --- Pathology ---
    "inflammation", "necrosis", "apoptosis", "edema", "fibrosis",
    "hyperplasia", "hypertrophy", "atrophy", "metaplasia", "dysplasia",
    "neoplasm", "benign", "malignant", "metastasis", "carcinoma",
    # --- Biochemistry ---
    "amino acid", "peptide bond", "polypeptide", "tertiary structure",
    "quaternary structure", "denaturation", "michaelis-menten",
    "allosteric", "competitive inhibition", "non-competitive inhibition",
    "gluconeogenesis", "glycogenolysis", "beta oxidation", "ketogenesis",
    "urea cycle", "pentose phosphate", "citric acid cycle",
    "fatty acid", "cholesterol", "phospholipid", "triglyceride",
    # --- Immunology ---
    "t cell", "b cell", "helper t cell", "cytotoxic t cell",
    "mhc class i", "mhc class ii", "humoral immunity", "cell mediated immunity",
    "hypersensitivity", "autoimmune", "tolerance", "vaccination",
    "immunoglobulin", "opsonization", "memory cell",
    "natural killer cell", "dendritic cell", "macrophage",
    # --- Genetics ---
    "allele", "genotype", "phenotype", "homozygous", "heterozygous",
    "dominant", "recessive", "codominant", "epistasis", "linkage",
    "crossing over", "restriction enzyme", "crispr",
    "mutation", "point mutation", "frameshift", "chromosomal",
    "meiosis", "mitosis", "ploidy", "karyotype",
    # --- Neuroscience ---
    "dopamine", "serotonin", "norepinephrine", "acetylcholine",
    "gaba", "glutamate", "blood brain barrier", "myelin",
    "saltatory conduction", "long term potentiation",
    "autonomic nervous system", "sympathetic", "parasympathetic",
    "reflex arc", "cerebral cortex", "hippocampus", "amygdala",
    # --- Endocrinology ---
    "hormone", "endocrine", "hypothalamus", "pituitary",
    "thyroid", "adrenal", "insulin", "glucagon",
    "cortisol", "aldosterone", "negative feedback", "positive feedback",
    "testosterone", "estrogen", "progesterone", "growth hormone",
    # --- Lab techniques ---
    "plaque assay", "pcr", "rt-pcr", "serology", "electron microscopy",
    "elisa", "western blot", "gel electrophoresis", "flow cytometry",
    "histology", "biopsy", "culture", "staining", "microscopy",
    "reverse transcriptase", "rna polymerase", "dna polymerase",
    "lysozyme", "neuraminidase",
}


# ---------------------------------------------------------------------------
# Sentence splitting
# ---------------------------------------------------------------------------

def split_into_sentences(text: str) -> list[str]:
    """Split transcript text into sentences.

    Handles the messy reality of lecture transcripts where sentences
    run together and abbreviations cause false splits.
    """
    # Protect common abbreviations from splitting
    protected = text
    abbrevs = ["e.g.", "i.e.", "etc.", "vs.", "Dr.", "Mr.", "Ms.", "Prof."]
    for abbr in abbrevs:
        protected = protected.replace(abbr, abbr.replace(".", "<<DOT>>"))

    # Split on sentence-ending punctuation followed by space + capital letter
    # or on "Okay" / "So" / "All right" which often start new thoughts in lectures
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])', protected)

    # Also split on "Okay." "So." "All right." when they start a new thought
    result = []
    for part in parts:
        # Restore protected dots
        part = part.replace("<<DOT>>", ".")
        result.append(part.strip())

    return [s for s in result if s]


# ---------------------------------------------------------------------------
# Marker detection and splitting
# ---------------------------------------------------------------------------

def detect_markers(text: str) -> list[dict]:
    """Scan text for topic transition markers.

    Returns list of {position, marker_type, matched_text, topic_hint} sorted by position.
    """
    sentences = split_into_sentences(text)
    markers = []

    # Track character position of each sentence in the original text
    pos = 0
    for sentence in sentences:
        idx = text.find(sentence, pos)
        if idx == -1:
            idx = pos

        # Check slide markers
        m = SLIDE_MARKER.search(sentence)
        if m:
            markers.append({
                "position": idx,
                "marker_type": "slide",
                "matched_text": sentence[:120],
                "topic_hint": extract_topic_hint(sentence),
            })
            pos = idx + len(sentence)
            continue

        # Check topic markers
        m = TOPIC_MARKER.search(sentence)
        if m:
            markers.append({
                "position": idx,
                "marker_type": "topic",
                "matched_text": sentence[:120],
                "topic_hint": extract_topic_hint(sentence),
            })
            pos = idx + len(sentence)
            continue

        # Check transition patterns
        for pattern in TRANSITION_PATTERNS:
            if pattern.search(sentence):
                markers.append({
                    "position": idx,
                    "marker_type": "transition",
                    "matched_text": sentence[:120],
                    "topic_hint": extract_topic_hint(sentence),
                })
                break

        pos = idx + len(sentence)

    # Sort by position and deduplicate nearby markers (within 300 chars)
    markers.sort(key=lambda m: m["position"])
    return deduplicate_markers(markers, min_gap=300)


def deduplicate_markers(markers: list[dict], min_gap: int = 500) -> list[dict]:
    """Remove markers that are too close together (likely same topic transition)."""
    if not markers:
        return markers

    result = [markers[0]]
    for m in markers[1:]:
        if m["position"] - result[-1]["position"] >= min_gap:
            result.append(m)
        else:
            # Keep the one with a better topic hint
            if len(m.get("topic_hint", "")) > len(result[-1].get("topic_hint", "")):
                result[-1] = m
    return result


def extract_topic_hint(sentence: str) -> str:
    """Try to extract a topic name from a transition sentence.

    e.g., "let's have a look at the envelope viruses" → "envelope viruses"
    e.g., "So we start off our first topic and that is viruses in general" → "viruses in general"
    """
    # Pattern: "... is/are [TOPIC]"
    m = re.search(r"(?:that\s+is|that\s+are|and\s+that\s+is)\s+(.+?)(?:\.|$)", sentence, re.IGNORECASE)
    if m:
        return clean_topic_hint(m.group(1))

    # Pattern: "look at / move on to / talk about [TOPIC]"
    m = re.search(r"(?:look\s+at|move\s+on\s+to|talk\s+about|deal\s+with|cover|go\s+(?:through|into))\s+(?:the\s+)?(.+?)(?:\.|okay|$)", sentence, re.IGNORECASE)
    if m:
        return clean_topic_hint(m.group(1))

    # Pattern: "back to [TOPIC]"
    m = re.search(r"back\s+to\s+(.+?)(?:\.|okay|$)", sentence, re.IGNORECASE)
    if m:
        return clean_topic_hint(m.group(1))

    # Pattern: "what's called [X]" or "according to [X]"
    m = re.search(r"(?:what's\s+called|called)\s+(?:the\s+)?(.+?)(?:\.|okay|it's|$)", sentence, re.IGNORECASE)
    if m:
        return clean_topic_hint(m.group(1))

    # Pattern: "[topic] of [subject]" near start of sentence
    m = re.search(r"(?:naming|classification|taxonomy|structure|function|replication|evolution|infection)\s+of\s+(.+?)(?:\.|okay|$)", sentence, re.IGNORECASE)
    if m:
        match_start = sentence.lower().find(m.group(0).lower())
        # Use the full phrase as the topic name
        return clean_topic_hint(m.group(0))

    # Fallback: first few meaningful words after transition phrase
    # Strip common transition prefixes
    cleaned = re.sub(
        r"^(?:okay|so|all\s+right|um|uh)[,.\s]*(?:so\s+)?",
        "", sentence, flags=re.IGNORECASE
    ).strip()
    words = cleaned.split()[:8]
    if words:
        return clean_topic_hint(" ".join(words))

    return ""


def clean_topic_hint(hint: str) -> str:
    """Clean up a topic hint string."""
    # Remove filler words and trailing junk
    hint = re.sub(r"\b(?:um|uh|okay|so|and|the|our|we|you|I|it's|that|etc|all right|well|now|just|going to|we're|they're|it|is|are|be|have|has|do|does|did|can|will|would|should|could|of|in|on|at|for|to|with|by|from|but|or|if|as|a|an)\b", "", hint, flags=re.IGNORECASE)
    hint = re.sub(r"\s+", " ", hint).strip()
    hint = hint.strip("., ;:'-")
    # Remove leading/trailing junk
    hint = re.sub(r"^[,.\s'-]+", "", hint)
    hint = re.sub(r"[,.\s'-]+$", "", hint)
    # Capitalize first letter
    if hint:
        hint = hint[0].upper() + hint[1:]
    # Limit to 60 chars, break at word boundary
    if len(hint) > 60:
        hint = hint[:60].rsplit(" ", 1)[0]
    return hint


def polish_topic_name(name: str, key_terms: list[str], text: str) -> str:
    """Final cleanup of topic names.

    If the name is still garbled (too many filler artifacts, weird apostrophes,
    or doesn't contain any meaningful words), try to derive a better name
    from the content itself.
    """
    # Fix common artifacts first
    name = re.sub(r"'\s*re\b", "", name)
    name = re.sub(r"'\s*s\b", "s", name)
    name = re.sub(r"\s+", " ", name).strip()

    # Check if name looks garbled
    words = name.split()
    filler = {"the", "and", "for", "are", "but", "not", "its", "this", "that", "was",
              "way", "see", "got", "get", "how", "what", "who", "why", "when", "where",
              "cover", "first", "two", "topics", "one", "here", "based", "includes",
              "named", "after", "name", "see", "class"}
    meaningful = [w for w in words if len(w) > 2 and w.lower() not in filler]

    is_garbled = (
        len(meaningful) < 2 and len(words) > 3  # mostly filler
        or any(c in name for c in ["'re", "'", "  "])  # artifacts
        or name.lower().startswith(("way ", "when ", "class one"))  # obvious garble
        or len(words) > 5  # too long = garbled
        or (len(words) >= 3 and any(
            name.lower().split().count(w) >= 2 for w in name.lower().split() if len(w) > 3
        ))  # any word repeated multiple times
        or re.search(r"\b(based|includes|see)\s*$", name.lower())  # trailing junk word
    )

    if is_garbled:
        # Try to derive a better name from content
        better = _derive_topic_from_content(text, key_terms)
        if better:
            return better
    elif name not in ("Introduction / Housekeeping",):
        # Even if not garbled, check if content derivation gives a more accurate name
        # (e.g., name says "DNA viruses" but content is about "Animal Virus Families")
        derived = _derive_topic_from_content(text, key_terms)
        if derived and derived.lower() != name.lower() and len(derived) > len(name):
            # Prefer the derived name if it's more specific
            return derived

    return name


def _name_topic_with_flash(text: str) -> str:
    """Use Gemini Flash to name a topic from transcript content — any discipline."""
    from google import genai
    from src.config import GCP_PROJECT_ID, GCP_LOCATION, CHUNKER_FALLBACK_MODEL

    prompt = (
        "What is the main topic of this lecture transcript excerpt? "
        "Give a short, descriptive topic name (2-5 words) suitable as a section heading. "
        "Examples: 'Muscle Contraction Types', 'Cell Membrane Structure', "
        "'Drug-Receptor Interactions', 'Inflammatory Response'.\n\n"
        "Return ONLY the topic name, nothing else.\n\n"
        f"TRANSCRIPT:\n\"\"\"\n{text[:1000]}\n\"\"\""
    )

    client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)
    response = client.models.generate_content(
        model=CHUNKER_FALLBACK_MODEL,
        contents=prompt,
        config={"temperature": 0.1, "max_output_tokens": 50},
    )
    name = response.text.strip().strip('"').strip("'")
    if 2 <= len(name.split()) <= 6 and len(name) < 60:
        return name
    raise ValueError(f"Flash returned invalid topic name: {name}")


def _derive_topic_from_content(text: str, key_terms: list[str], use_llm: bool = True) -> str | None:
    """Derive a topic name by looking at what the text is actually about.

    Primary: Uses Gemini Flash for topic naming — works for ANY discipline.
    Fallback: Uses regex pattern matching.
    """
    # Try LLM first — it can name topics in any medical discipline
    if use_llm:
        try:
            return _name_topic_with_flash(text)
        except Exception:
            pass  # fall through to regex

    text_lower = text[:2000].lower()  # only scan the beginning

    # Topic patterns for ANY biomedical lecture (not just microbiology).
    # General patterns first, then discipline-specific ones.
    # The chunker also uses LLM fallback for topic naming when these don't match.
    topic_patterns = [
        # --- Course structure (any lecture) ---
        (r"(?:structure|function)\s+of\s+\w+", "Course Overview"),
        (r"module\s+(?:one|two|three|four|1|2|3|4)", "Module Overview"),
        (r"(?:overall|general)\s+(?:process|overview|introduction)", "Overview"),

        # --- General biology patterns (any biomedical lecture) ---
        (r"classification\s+(?:system|of|criteria)", "Classification System"),
        (r"how\s+(?:do\s+)?we\s+classify", "Classification Criteria"),
        (r"naming\s+(?:conventions?|of)", "Naming Conventions"),
        (r"(?:life|replication|reproductive)\s+cycle", "Life Cycles"),
        (r"(?:infection|entry)\s+(?:process|mechanism)", "Infection Mechanism"),
        (r"(?:structure|anatomy)\s+of", "Structure & Anatomy"),
        (r"(?:function|role)\s+of", "Function & Role"),
        (r"types?\s+of\s+\w+", "Types & Classification"),
        (r"(?:evolution|origin)s?\s+(?:of|and)", "Evolution & Origins"),
        (r"(?:size|morphology)\s+(?:of|and|range)", "Size & Morphology"),

        # --- Microbiology-specific ---
        (r"baltimore\s+classification", "Baltimore Classification System"),
        (r"lytic\s+.*?lysogenic|lysogenic\s+.*?lytic", "Lytic vs Lysogenic Cycles"),
        (r"bacteriophage|phage\s+infect", "Bacteriophage Infection"),
        (r"envelope\s+virus", "Envelope Viruses"),
        (r"(?:animal|human)\s+virus", "Animal Virus Families"),
        (r"(?:dna|rna)\s+virus(?:es)?", "Virus Families"),

        # --- Anatomy/physiology-specific ---
        (r"muscle\s+contraction", "Muscle Contraction"),
        (r"(?:skeletal|cardiac|smooth)\s+muscle", "Muscle Types"),
        (r"(?:action|resting)\s+potential", "Membrane Potential"),
        (r"(?:blood|cardiac)\s+(?:flow|cycle|output)", "Cardiovascular Function"),
        (r"(?:nerve|neural)\s+(?:impulse|signal|pathway)", "Neural Signaling"),
        (r"(?:respiratory|gas)\s+exchange", "Respiratory Function"),
        (r"immune\s+(?:response|system|defense)", "Immune Response"),

        # --- Pharmacology-specific ---
        (r"(?:drug|receptor)\s+(?:binding|interaction)", "Drug-Receptor Interaction"),
        (r"(?:pharmacokinetics|absorption.*?distribution)", "Pharmacokinetics"),
        (r"(?:dose|therapeutic)\s+(?:response|index)", "Dose-Response"),

        # --- Pathology-specific ---
        (r"(?:inflammation|inflammatory)\s+(?:response|process)", "Inflammatory Response"),
        (r"(?:neoplasia|tumor|cancer)\s+(?:development|growth)", "Neoplasia"),
        (r"(?:necrosis|apoptosis|cell\s+death)", "Cell Death Mechanisms"),

        # --- Biochemistry-specific ---
        (r"enzyme\s+(?:kinetics|regulation|inhibition)", "Enzyme Kinetics"),
        (r"(?:amino\s+acid|protein)\s+(?:structure|folding)", "Protein Structure"),
        (r"(?:metabolic|catabolic|anabolic)\s+pathway", "Metabolic Pathways"),
        (r"(?:krebs|citric\s+acid|tca)\s+cycle", "Citric Acid Cycle"),
        (r"(?:glycolysis|gluconeogenesis|glycogen)", "Glucose Metabolism"),
        (r"(?:fatty\s+acid|lipid)\s+(?:metabolism|oxidation|synthesis)", "Lipid Metabolism"),

        # --- Immunology-specific ---
        (r"(?:innate|adaptive|humoral|cell.mediated)\s+immun", "Immune Response"),
        (r"(?:t\s+cell|b\s+cell|lymphocyte)\s+(?:activation|differentiation)", "Lymphocyte Biology"),
        (r"(?:antigen|antibody)\s+(?:presentation|recognition)", "Antigen Recognition"),
        (r"(?:mhc|major\s+histocompatibility)", "MHC & Antigen Presentation"),
        (r"(?:hypersensitivity|allerg)", "Hypersensitivity Reactions"),

        # --- Genetics-specific ---
        (r"(?:mendelian|non.mendelian)\s+(?:genetics|inheritance)", "Inheritance Patterns"),
        (r"(?:gene|dna)\s+(?:regulation|expression)", "Gene Regulation"),
        (r"(?:chromosom|karyotype|ploidy)", "Chromosomal Biology"),
        (r"(?:mutation|mutagenesis)", "Mutations & Mutagenesis"),

        # --- Neuroscience-specific ---
        (r"(?:synaptic|neural)\s+(?:transmission|plasticity)", "Synaptic Transmission"),
        (r"(?:autonomic|somatic)\s+nervous", "Autonomic Nervous System"),
        (r"(?:dopamine|serotonin|neurotransmitter)\s+(?:pathway|system)", "Neurotransmitter Systems"),

        # --- Endocrinology-specific ---
        (r"(?:hormone|endocrine)\s+(?:regulation|signaling|system)", "Endocrine Regulation"),
        (r"(?:hypothalamic|pituitary|thyroid|adrenal)\s+(?:axis|function)", "Endocrine Axis"),
        (r"(?:insulin|glucagon|diabetes)", "Glucose Homeostasis"),
    ]

    for pattern, name in topic_patterns:
        if re.search(pattern, text_lower):
            return name

    # Fallback: use the most distinctive key term
    specific = sorted(
        [t for t in key_terms if len(t) > 8 and " " in t],
        key=len, reverse=True
    )
    if specific:
        return specific[0].title()

    return None


def split_on_markers(text: str, markers: list[dict]) -> list[dict]:
    """Split transcript text at marker positions into raw chunks."""
    if not markers:
        return [{"topic_hint": "Full Transcript", "text": text}]

    chunks = []
    for i, marker in enumerate(markers):
        start = marker["position"]
        end = markers[i + 1]["position"] if i + 1 < len(markers) else len(text)
        chunk_text = text[start:end].strip()

        if len(chunk_text) < 50:  # skip tiny fragments
            continue

        chunks.append({
            "topic_hint": marker.get("topic_hint", f"Section {i+1}"),
            "text": chunk_text,
        })

    # Handle text before the first marker (preamble)
    if markers[0]["position"] > 200:
        preamble = text[:markers[0]["position"]].strip()
        if len(preamble) > 50:
            chunks.insert(0, {
                "topic_hint": "Introduction / Housekeeping",
                "text": preamble,
            })

    return chunks


# ---------------------------------------------------------------------------
# Emphasis extraction (zero tokens)
# ---------------------------------------------------------------------------

def extract_emphasis(text: str) -> tuple[str, list[EmphasisSignal]]:
    """Extract emphasis signals from a chunk of text.

    Returns (emphasis_score, list_of_signals).
    """
    signals = []
    sentences = split_into_sentences(text)

    positive_count = 0
    negative_count = 0

    for sentence in sentences:
        # Check positive emphasis
        for pattern, keyword in EMPHASIS_POSITIVE:
            if pattern.search(sentence):
                signals.append(EmphasisSignal(
                    keyword=keyword,
                    context=sentence[:150],
                    sentiment="positive",
                ))
                positive_count += 1

        # Check negative emphasis
        for pattern, keyword in EMPHASIS_NEGATIVE:
            if pattern.search(sentence):
                signals.append(EmphasisSignal(
                    keyword=keyword,
                    context=sentence[:150],
                    sentiment="negative",
                ))
                negative_count += 1

    # Detect the contradictory professor pattern:
    # "I want you to know X" + "don't memorize X" in the same chunk
    # This means: UNDERSTAND the concept deeply, just don't rote-memorize a table.
    # For a student, this is HARDER than memorizing — so it's HIGH importance.
    has_contradiction = positive_count > 0 and negative_count > 0

    # Check if this is a complex/mechanism topic (these need deep understanding)
    text_lower = text.lower()
    # Detect complex topics across ANY biomedical discipline
    # These keywords signal multi-step mechanisms that need deep understanding
    is_complex_topic = any(kw in text_lower for kw in [
        "mechanism", "pathway", "cycle", "process", "cascade",
        "classification", "categories", "types of", "classes of",
        "step one", "step two", "step 1", "step 2", "first step",
        "phase one", "phase two", "phase 1", "phase 2",
        "positive sense", "negative sense", "depolarization",
        "feedback loop", "signal transduction", "replication",
    ])

    # Score based on signals
    if has_contradiction and is_complex_topic:
        # Professor said "understand but don't memorize" on a complex topic
        # This is the MOST important type — needs deep explanation, not a table
        score = "HIGH"
        signals.append(EmphasisSignal(
            keyword="contradictory emphasis",
            context="Professor said both 'need to know' and 'don't memorize' — means understand deeply, not skip",
            sentiment="positive",
        ))
    elif negative_count > positive_count and not is_complex_topic:
        score = "LOW"
    elif positive_count >= 2:
        score = "HIGH"
    elif positive_count == 1:
        score = "MEDIUM"
    elif has_contradiction:
        # Contradiction on a non-complex topic — still medium
        score = "MEDIUM"
    else:
        # No explicit signals — use word count as proxy
        # But INVERT the professor's time allocation:
        # Professor yaps long on easy stuff and skims hard stuff
        # So word count is a WEAK signal, not a strong one
        word_count = len(text.split())
        if word_count > 1500:
            score = "MEDIUM"  # long ≠ important, professor might be rambling
        elif word_count > 500:
            score = "MEDIUM"
        else:
            score = "MEDIUM"  # short ≠ unimportant, professor might be skimming

    return score, signals


# ---------------------------------------------------------------------------
# Term extraction and prerequisite mapping (zero tokens)
# ---------------------------------------------------------------------------

def extract_technical_terms(text: str, use_llm: bool = True) -> list[str]:
    """Extract technical/scientific terms from text.

    Primary: Uses Gemini Flash to extract exam-relevant medical/scientific terms.
    Fallback: Uses seed terms + heuristics if LLM fails.
    Flash cost: ~100 tokens per chunk — negligible.
    """
    if use_llm:
        try:
            return _extract_terms_with_flash(text)
        except Exception as e:
            print(f"  Flash term extraction failed, falling back to heuristic: {e}")

    # Fallback: seed terms + regex heuristics
    return _extract_terms_heuristic(text)


def _extract_terms_with_flash(text: str) -> list[str]:
    """Use Gemini Flash to extract technical terms — works for ANY medical discipline."""
    from google import genai
    from src.config import GCP_PROJECT_ID, GCP_LOCATION, CHUNKER_FALLBACK_MODEL
    import json as _json

    prompt = (
        "Extract the technical and medical terms from this lecture transcript excerpt "
        "that a student would need to know for an exam. Include scientific names, "
        "processes, structures, classifications, techniques, and diseases.\n\n"
        "Return ONLY a JSON array of strings, e.g.: [\"mitochondria\", \"action potential\", \"endocytosis\"]\n\n"
        f"TRANSCRIPT:\n\"\"\"\n{text[:2000]}\n\"\"\""
    )

    client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)
    response = client.models.generate_content(
        model=CHUNKER_FALLBACK_MODEL,
        contents=prompt,
        config={"temperature": 0.1, "max_output_tokens": 512},
    )
    from src.json_repair import extract_json
    terms = extract_json(response.text, expect_array=True)
    return sorted(set(str(t).lower().strip() for t in terms if t))


def _extract_terms_heuristic(text: str) -> list[str]:
    """Fallback: extract terms using seed list + regex patterns."""
    text_lower = text.lower()
    found = []

    for term in SEED_TERMS:
        if term in text_lower:
            found.append(term)

    # Heuristic: find capitalized multi-word phrases that look technical
    tech_phrases = re.findall(r'[A-Z][a-z]+(?:\s+[a-z]+){0,2}(?:\s+[A-Z][a-z]+)*', text)
    for phrase in tech_phrases:
        p_lower = phrase.lower()
        if len(p_lower) > 4 and p_lower not in {"okay", "well", "yeah", "right", "sorry"}:
            if any(w in p_lower for w in ["protein", "acid", "cell", "gene",
                                           "membrane", "cycle", "ase", "osis", "tion", "ular"]):
                found.append(p_lower)

    return sorted(set(found))


def map_prerequisites(chunks: list[dict]) -> dict[int, dict]:
    """Map prerequisites and forward references across chunks.

    Returns {chunk_index: {"prerequisites": [...], "forward_refs": [...], "reorder": ...}}
    """
    # Build term → first_chunk_index mapping
    term_first_chunk: dict[str, int] = {}
    chunk_terms: dict[int, list[str]] = {}

    for i, chunk in enumerate(chunks):
        terms = extract_technical_terms(chunk["text"])
        chunk_terms[i] = terms
        for term in terms:
            if term not in term_first_chunk:
                term_first_chunk[term] = i

    # For each chunk, find prerequisites and forward references
    result = {}
    for i, chunk in enumerate(chunks):
        terms = chunk_terms[i]
        prerequisites = []
        forward_refs = []

        for term in terms:
            first_chunk = term_first_chunk.get(term, i)
            if first_chunk < i:
                prerequisites.append(term)
            elif first_chunk > i:
                # This chunk uses a term that's first properly introduced later
                forward_refs.append(term)

        reorder = None
        if forward_refs:
            # Find which later chunk introduces the most forward-referenced terms
            later_chunks = Counter()
            for term in forward_refs:
                later_chunks[term_first_chunk[term]] += 1
            if later_chunks:
                most_common_later = later_chunks.most_common(1)[0]
                later_idx, count = most_common_later
                if count >= 2:  # only flag if multiple terms point to same later chunk
                    reorder = f"Uses {count} terms first introduced in chunk {later_idx} ({chunks[later_idx]['topic_hint']})"

        result[i] = {
            "prerequisites": prerequisites,
            "forward_refs": forward_refs,
            "reorder": reorder,
        }

    return result


# ---------------------------------------------------------------------------
# Post-processing: merge tiny chunks, flag oversized ones
# ---------------------------------------------------------------------------

def merge_tiny_chunks(chunks: list[dict], min_words: int = 150) -> list[dict]:
    """Merge chunks that are too small to stand alone.

    A chunk under min_words gets merged into the next chunk (it's likely a
    transition sentence that belongs with the following topic).
    """
    if len(chunks) <= 1:
        return chunks

    merged = []
    carry = None  # text to prepend to the next chunk

    for chunk in chunks:
        word_count = len(chunk["text"].split())

        if carry:
            # Prepend carried text to this chunk
            chunk = {
                "topic_hint": chunk["topic_hint"],
                "text": carry + "\n\n" + chunk["text"],
            }
            carry = None

        if word_count < min_words:
            # Too small — carry forward to merge with next chunk
            carry = chunk["text"]
        else:
            merged.append(chunk)

    # If the last chunk was tiny, append to the previous one
    if carry and merged:
        merged[-1]["text"] += "\n\n" + carry
    elif carry:
        merged.append({"topic_hint": "Final Section", "text": carry})

    return merged


# ---------------------------------------------------------------------------
# Sub-chunking: split complex topics into finer pieces
# ---------------------------------------------------------------------------

# Patterns that indicate a chunk covers multiple enumerated sub-concepts
# Each pattern: (detection_regex, split_regex, name_template)
def detect_multi_concept_chunks(chunks: list[dict]) -> list[dict]:
    """Detect chunks that cover multiple distinct concepts.

    These are candidates for sub-chunking via Gemini Flash.
    An LLM can't explain 7 things at once — each concept needs its own chunk.

    Detection heuristics (zero tokens):
    1. Enumerated items: "class 1", "class 2", "step 1", "type A", "type B"
    2. Multiple comparison subjects: "gram positive vs gram negative"
    3. Multiple mechanisms in one block: "lytic cycle... lysogenic cycle..."
    4. High word count with multiple technical terms introduced
    """
    # Patterns that indicate multiple concepts in one chunk
    multi_concept_patterns = [
        # Enumerated classes/types/groups
        re.compile(r"class\s+(?:one|two|three|four|five|six|seven|1|2|3|4|5|6|7)\b", re.IGNORECASE),
        # Numbered steps
        re.compile(r"(?:step|stage|phase)\s+(?:one|two|three|four|five|\d+)\b", re.IGNORECASE),
        # Type/group enumerations
        re.compile(r"(?:type|group|category)\s+(?:one|two|three|four|five|[A-E]|\d+)\b", re.IGNORECASE),
        # Named distinct mechanisms/processes
        re.compile(r"\b(?:lytic|lysogenic|acute|latent|persistent|chronic)\b", re.IGNORECASE),
        # Entry mechanisms
        re.compile(r"\b(?:membrane\s+fusion|endocytosis|genome\s+injection|budding)\b", re.IGNORECASE),
    ]

    for chunk in chunks:
        text = chunk["text"]
        word_count = len(text.split())

        # Skip small chunks
        if word_count < 300:
            continue

        # Count distinct concept indicators
        all_matches = []
        for pattern in multi_concept_patterns:
            matches = pattern.findall(text)
            unique = set(m.lower() for m in matches)
            if len(unique) >= 2:
                all_matches.extend(unique)

        distinct_concepts = len(set(all_matches))

        if distinct_concepts >= 3:
            words_per_concept = word_count // distinct_concepts
            chunk["needs_sub_chunking"] = True
            chunk["concept_count"] = distinct_concepts
            chunk["words_per_concept"] = words_per_concept

        # Mega-chunk override: any chunk over 2000 words almost certainly
        # covers multiple topics even if the regex patterns don't catch them.
        # The professor rambles across topic boundaries without clear markers.
        elif word_count > 1500 and not chunk.get("needs_sub_chunking"):
            chunk["needs_sub_chunking"] = True
            chunk["concept_count"] = max(3, word_count // 500)
            chunk["words_per_concept"] = 500

    return chunks


def sub_chunk_with_llm(chunks: list[dict], use_llm: bool = True) -> list[dict]:
    """Sub-chunk multi-concept chunks using Gemini Flash.

    For each chunk flagged with needs_sub_chunking, ask Gemini Flash to
    identify the distinct concepts and their text boundaries. This costs
    ~500 tokens per chunk — only runs on flagged chunks.

    If use_llm=False, falls back to keeping the chunk as-is with an
    expansion hint for Stage 2.
    """
    result = []

    for chunk in chunks:
        if not chunk.get("needs_sub_chunking"):
            result.append(chunk)
            continue

        if not use_llm:
            # Fallback: just flag for Stage 2 expansion
            chunk["needs_expansion"] = True
            chunk["expansion_hint"] = (
                f"Covers ~{chunk['concept_count']} distinct concepts in {len(chunk['text'].split())} words "
                f"(~{chunk['words_per_concept']} words each). Professor skimmed these — "
                f"Stage 2 should generate a separate explanation for each concept."
            )
            result.append(chunk)
            continue

        # Use Gemini Flash to sub-chunk
        sub_chunks = _llm_sub_chunk(chunk)
        if sub_chunks:
            result.extend(sub_chunks)
        else:
            # LLM call failed — fall back to expansion hint
            chunk["needs_expansion"] = True
            chunk["expansion_hint"] = (
                f"Covers ~{chunk['concept_count']} distinct concepts. "
                f"LLM sub-chunking failed — Stage 2 should expand each concept separately."
            )
            result.append(chunk)

    return result


def _llm_sub_chunk(chunk: dict) -> list[dict] | None:
    """Use Gemini Flash via Vertex AI to split a multi-concept chunk.

    Returns a list of sub-chunks, or None if the call fails.
    """
    try:
        from google import genai
        from src.config import GCP_PROJECT_ID, GCP_LOCATION, CHUNKER_FALLBACK_MODEL

        if not GCP_PROJECT_ID:
            print("WARNING: GCP_PROJECT_ID not set. Skipping LLM sub-chunking.")
            return None

        client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)

        prompt = f"""You are splitting a lecture transcript chunk into separate sub-topics.
This chunk covers multiple distinct concepts that each need their own explanation.

TRANSCRIPT CHUNK:
\"\"\"
{chunk['text'][:12000]}
\"\"\"

Split this into separate sub-topics. For each sub-topic, provide:
1. A short topic name (3-8 words)
2. The START and END character positions in the text above

Return ONLY a JSON array like this (no other text):
[
  {{"name": "Topic Name Here", "start": 0, "end": 500}},
  {{"name": "Another Topic", "start": 501, "end": 1200}}
]

Rules:
- Each sub-topic should cover ONE distinct concept, mechanism, or classification
- Don't split mid-sentence
- Every character of the text should be covered (no gaps)
- Minimum 3 sub-topics, maximum 10
"""

        response = client.models.generate_content(model=CHUNKER_FALLBACK_MODEL, contents=prompt)
        from src.json_repair import extract_json
        splits = extract_json(response.text, expect_array=True)

        if not isinstance(splits, list) or len(splits) < 2:
            return None

        # Build sub-chunks from the split positions
        text = chunk["text"]
        sub_chunks = []
        for split in splits:
            start = max(0, int(split.get("start", 0)))
            end = min(len(text), int(split.get("end", len(text))))
            sub_text = text[start:end].strip()

            if len(sub_text.split()) < 20:  # skip tiny fragments
                continue

            sub_chunks.append({
                "topic_hint": split.get("name", "Sub-topic"),
                "text": sub_text,
                "parent_topic": chunk.get("topic_hint", ""),
                "is_sub_chunk": True,
            })

        return sub_chunks if len(sub_chunks) >= 2 else None

    except Exception as e:
        print(f"WARNING: LLM sub-chunking failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def chunk_transcript(text: str, use_llm: bool = True) -> list[Chunk]:
    """Full Stage 1 pipeline: detect markers, split, extract metadata.

    Mostly token-free. Uses Gemini Flash only for:
    1. Fallback chunking when no regex markers found
    2. Sub-chunking multi-concept chunks (one concept per chunk)

    Set use_llm=False to skip all LLM calls (will flag for Stage 2 expansion instead).
    """
    # Step 1: Detect markers
    markers = detect_markers(text)

    if len(markers) < 3:
        # Not enough markers for meaningful chunking
        # TODO: Fall back to Vertex AI Gemini Flash
        print(f"WARNING: Only {len(markers)} markers found. Consider using LLM fallback.")
        # For now, try to split on paragraph-level patterns
        if len(markers) == 0:
            # Last resort: split on long "Okay. So" breaks
            markers = _fallback_split_points(text)

    # Step 2: Split on markers
    raw_chunks = split_on_markers(text, markers)

    # Step 2b: Post-process — merge tiny chunks
    raw_chunks = merge_tiny_chunks(raw_chunks, min_words=100)

    # Step 2c: Detect multi-concept chunks and sub-chunk them
    raw_chunks = detect_multi_concept_chunks(raw_chunks)
    raw_chunks = sub_chunk_with_llm(raw_chunks, use_llm=use_llm)

    # Step 2d: Merge any tiny sub-chunks created by LLM splitting
    raw_chunks = merge_tiny_chunks(raw_chunks, min_words=80)

    # Step 3: Map prerequisites across all chunks
    prereq_map = map_prerequisites(raw_chunks)

    # Step 4: Build Chunk objects with all metadata
    chunks = []
    for i, raw in enumerate(raw_chunks):
        emphasis_score, emphasis_signals = extract_emphasis(raw["text"])
        key_terms = extract_technical_terms(raw["text"])
        prereq_data = prereq_map.get(i, {"prerequisites": [], "forward_refs": [], "reorder": None})

        # Polish the topic name — if it's still garbled, derive from key terms
        topic_name = raw["topic_hint"] or f"Section {i+1}"
        topic_name = polish_topic_name(topic_name, key_terms, raw["text"])

        chunks.append(Chunk(
            chunk_index=i,
            topic_name=topic_name,
            transcript_text=raw["text"],
            word_count=len(raw["text"].split()),
            emphasis_score=emphasis_score,
            emphasis_signals=emphasis_signals,
            key_terms=key_terms,
            prerequisites=prereq_data["prerequisites"],
            forward_references=prereq_data["forward_refs"],
            reorder_suggestion=prereq_data["reorder"],
            needs_expansion=raw.get("needs_expansion", False),
            expansion_hint=raw.get("expansion_hint"),
            is_sub_chunk=raw.get("is_sub_chunk", False),
            parent_topic=raw.get("parent_topic"),
        ))

    return chunks


def _fallback_split_points(text: str) -> list[dict]:
    """Emergency fallback: split on major pause patterns when no markers found."""
    # Split on patterns like "Okay. So," which professors use between topics
    split_pattern = re.compile(r'(?:Okay\.\s+So,?\s+|All right\.\s+(?:So|Okay))', re.IGNORECASE)

    markers = []
    for m in split_pattern.finditer(text):
        markers.append({
            "position": m.start(),
            "marker_type": "fallback",
            "matched_text": text[m.start():m.start()+100],
            "topic_hint": extract_topic_hint(text[m.start():m.start()+200]),
        })

    return deduplicate_markers(markers, min_gap=1000)
