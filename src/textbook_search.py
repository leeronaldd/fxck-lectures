"""Textbook search: find and cache relevant textbook content for any medical topic.

Uses a comprehensive OpenStax chapter index + keyword matching.
Falls back to NCBI Bookshelf API for topics not covered by OpenStax.
Caches fetched content on disk.
"""

import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from src.config import GCP_PROJECT_ID, GCP_LOCATION, CHUNKER_FALLBACK_MODEL


# ---------------------------------------------------------------------------
# OpenStax chapter index — comprehensive coverage across medical disciplines
# ---------------------------------------------------------------------------

_OPENSTAX_BASE = "https://openstax.org/books"

# Each entry: (keywords, url) — keywords are matched against topic names
OPENSTAX_INDEX = [
    # === MICROBIOLOGY ===
    (["virus", "viruses", "viral", "virology"], f"{_OPENSTAX_BASE}/microbiology/pages/6-1-viruses"),
    (["viral life cycle", "viral replication", "lytic", "lysogenic", "bacteriophage"],
     f"{_OPENSTAX_BASE}/microbiology/pages/6-2-the-viral-life-cycle"),
    (["viral isolation", "animal virus", "virus identification"],
     f"{_OPENSTAX_BASE}/microbiology/pages/6-3-isolation-culture-and-identification-of-viruses"),
    (["prokaryotic", "prokaryote", "bacteria structure", "cell wall", "peptidoglycan"],
     f"{_OPENSTAX_BASE}/microbiology/pages/3-3-unique-characteristics-of-prokaryotic-cells"),
    (["eukaryotic", "eukaryote"], f"{_OPENSTAX_BASE}/microbiology/pages/3-4-unique-characteristics-of-eukaryotic-cells"),
    (["microscopy", "microscope"], f"{_OPENSTAX_BASE}/microbiology/pages/2-1-the-properties-of-light"),
    (["bacterial growth", "microbial growth"], f"{_OPENSTAX_BASE}/microbiology/pages/9-1-how-microbes-grow"),
    (["antibiotic", "antimicrobial", "chemotherapy"],
     f"{_OPENSTAX_BASE}/microbiology/pages/14-2-fundamentals-of-antimicrobial-chemotherapy"),
    (["innate immunity", "innate defense", "nonspecific defense"],
     f"{_OPENSTAX_BASE}/microbiology/pages/17-1-innate-nonspecific-host-defenses"),
    (["inflammation", "fever", "inflammatory"],
     f"{_OPENSTAX_BASE}/microbiology/pages/17-4-inflammation-and-fever"),
    (["adaptive immunity", "specific immunity", "acquired immunity"],
     f"{_OPENSTAX_BASE}/microbiology/pages/18-1-overview-of-specific-adaptive-immunity"),
    (["t cell", "t lymphocyte", "cell mediated", "cellular immunity"],
     f"{_OPENSTAX_BASE}/microbiology/pages/18-3-t-lymphocytes-and-cellular-immunity"),
    (["b cell", "b lymphocyte", "antibody", "humoral", "immunoglobulin"],
     f"{_OPENSTAX_BASE}/microbiology/pages/18-4-b-lymphocytes-and-humoral-immunity"),
    (["vaccine", "vaccination", "immunization"],
     f"{_OPENSTAX_BASE}/microbiology/pages/18-5-vaccines"),
    (["hypersensitivity", "allergy", "allergic", "autoimmune"],
     f"{_OPENSTAX_BASE}/microbiology/pages/19-1-hypersensitivities"),
    (["biofilm", "quorum sensing"], f"{_OPENSTAX_BASE}/microbiology/pages/9-4-biofilms"),
    (["conjugation", "transduction", "transformation", "horizontal gene transfer"],
     f"{_OPENSTAX_BASE}/microbiology/pages/11-6-gene-transfer-in-prokaryotes"),
    (["dna replication"], f"{_OPENSTAX_BASE}/microbiology/pages/11-2-dna-replication"),
    (["transcription", "rna synthesis"], f"{_OPENSTAX_BASE}/microbiology/pages/11-3-rna-transcription"),
    (["translation", "protein synthesis"], f"{_OPENSTAX_BASE}/microbiology/pages/11-4-protein-synthesis-translation"),
    (["endotoxin", "exotoxin", "toxin", "gram positive", "gram negative"],
     f"{_OPENSTAX_BASE}/microbiology/pages/15-3-virulence-factors-of-bacterial-and-viral-pathogens"),

    # === ANATOMY & PHYSIOLOGY ===
    (["muscle", "contraction", "skeletal muscle", "muscle fiber"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/10-1-overview-of-muscle-tissues"),
    (["muscle contraction", "sliding filament", "sarcomere"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/10-3-muscle-fiber-contraction-and-relaxation"),
    (["bone", "skeletal system", "ossification"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/6-3-bone-structure"),
    (["neuron", "nervous system", "neural"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/12-1-basic-structure-and-function-of-the-nervous-system"),
    (["action potential", "depolarization", "repolarization", "membrane potential"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/12-4-the-action-potential"),
    (["synapse", "synaptic", "neurotransmitter"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/12-5-communication-between-neurons"),
    (["autonomic", "sympathetic", "parasympathetic"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/15-1-divisions-of-the-autonomic-nervous-system"),
    (["cardiac", "heart", "cardiovascular"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/19-1-heart-anatomy"),
    (["cardiac cycle", "systole", "diastole", "blood pressure"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/19-3-cardiac-cycle"),
    (["blood vessel", "artery", "vein", "capillary", "vascular"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/20-1-structure-and-function-of-blood-vessels"),
    (["respiratory", "lung", "breathing", "ventilation", "alveoli"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/22-1-organs-and-structures-of-the-respiratory-system"),
    (["gas exchange", "oxygen transport"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/22-4-gas-exchange"),
    (["digestive", "digestion", "gastrointestinal", "stomach", "intestine"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/23-1-overview-of-the-digestive-system"),
    (["renal", "kidney", "nephron", "urine", "urinary"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/25-1-internal-and-external-anatomy-of-the-kidney"),
    (["endocrine", "hormone", "pituitary", "hypothalamus"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/17-1-an-overview-of-the-endocrine-system"),
    (["thyroid", "parathyroid", "calcitonin"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/17-4-the-thyroid-gland"),
    (["adrenal", "cortisol", "aldosterone", "epinephrine"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/17-6-the-adrenal-glands"),
    (["insulin", "glucagon", "pancreas", "diabetes", "glucose homeostasis"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/17-9-the-endocrine-pancreas"),
    (["reproductive", "testosterone", "estrogen", "ovary", "testes"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/27-1-anatomy-and-physiology-of-the-male-reproductive-system"),
    (["blood", "erythrocyte", "leukocyte", "platelet", "hemoglobin", "hematopoiesis"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/18-1-an-overview-of-blood"),
    (["lymphatic", "lymph node", "spleen", "thymus"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/21-1-anatomy-of-the-lymphatic-and-immune-systems"),
    (["immune response", "immune system"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/21-2-barrier-defenses-and-the-innate-immune-response"),
    (["fluid", "electrolyte", "acid base", "ph", "buffer"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/26-1-body-fluids-and-fluid-compartments"),
    (["homeostasis", "feedback", "negative feedback", "positive feedback"],
     f"{_OPENSTAX_BASE}/anatomy-and-physiology-2e/pages/1-5-homeostasis"),

    # === BIOLOGY (cell bio, genetics, biochemistry) ===
    (["cell membrane", "phospholipid", "membrane transport", "osmosis"],
     f"{_OPENSTAX_BASE}/biology-2e/pages/5-1-components-and-structure-of-cell-membranes"),
    (["mitosis", "cell division", "cell cycle"],
     f"{_OPENSTAX_BASE}/biology-2e/pages/10-1-cell-division"),
    (["meiosis", "crossing over", "recombination"],
     f"{_OPENSTAX_BASE}/biology-2e/pages/11-1-the-process-of-meiosis"),
    (["mendel", "inheritance", "allele", "genotype", "phenotype", "dominant", "recessive"],
     f"{_OPENSTAX_BASE}/biology-2e/pages/12-1-mendels-experiments-and-the-laws-of-probability"),
    (["gene expression", "gene regulation", "operon", "epigenetic"],
     f"{_OPENSTAX_BASE}/biology-2e/pages/16-1-regulation-of-gene-expression"),
    (["mutation", "dna repair", "mutagen"],
     f"{_OPENSTAX_BASE}/biology-2e/pages/14-6-dna-repair"),
    (["pcr", "gel electrophoresis", "cloning", "restriction enzyme", "biotechnology", "crispr"],
     f"{_OPENSTAX_BASE}/biology-2e/pages/17-1-biotechnology"),
    (["glycolysis", "glucose", "fermentation"],
     f"{_OPENSTAX_BASE}/biology-2e/pages/7-2-glycolysis"),
    (["citric acid cycle", "krebs", "tca"],
     f"{_OPENSTAX_BASE}/biology-2e/pages/7-3-oxidation-of-pyruvate-and-the-citric-acid-cycle"),
    (["electron transport", "oxidative phosphorylation", "atp synthase"],
     f"{_OPENSTAX_BASE}/biology-2e/pages/7-4-oxidative-phosphorylation"),
    (["photosynthesis", "chloroplast", "calvin cycle"],
     f"{_OPENSTAX_BASE}/biology-2e/pages/8-1-overview-of-photosynthesis"),
    (["enzyme", "enzyme kinetics", "michaelis", "substrate", "active site", "inhibition"],
     f"{_OPENSTAX_BASE}/biology-2e/pages/6-2-activation-energy"),
    (["protein structure", "amino acid", "polypeptide", "denaturation"],
     f"{_OPENSTAX_BASE}/biology-2e/pages/3-4-proteins"),
    (["lipid", "fatty acid", "cholesterol", "triglyceride"],
     f"{_OPENSTAX_BASE}/biology-2e/pages/3-3-lipids"),
    (["carbohydrate", "monosaccharide", "polysaccharide", "glycogen"],
     f"{_OPENSTAX_BASE}/biology-2e/pages/3-2-carbohydrates"),
    (["nucleic acid", "dna structure", "rna structure", "nucleotide"],
     f"{_OPENSTAX_BASE}/biology-2e/pages/3-5-nucleic-acids"),
    (["signal transduction", "cell signaling", "receptor"],
     f"{_OPENSTAX_BASE}/biology-2e/pages/9-1-signaling-molecules-and-cellular-receptors"),

    # === CHEMISTRY (biochemistry foundations) ===
    (["chemical bond", "covalent", "ionic", "hydrogen bond"],
     f"{_OPENSTAX_BASE}/chemistry-2e/pages/7-1-ionic-bonding"),
    (["acid", "base", "ph scale", "buffer solution"],
     f"{_OPENSTAX_BASE}/chemistry-2e/pages/14-1-bronsted-lowry-acids-and-bases"),
    (["oxidation", "reduction", "redox"],
     f"{_OPENSTAX_BASE}/chemistry-2e/pages/4-2-classifying-chemical-reactions"),

    # === PSYCHOLOGY ===
    (["conditioning", "classical conditioning", "operant", "pavlov", "skinner"],
     f"{_OPENSTAX_BASE}/psychology-2e/pages/6-1-what-is-learning"),
    (["memory", "encoding", "retrieval", "long term memory", "short term memory"],
     f"{_OPENSTAX_BASE}/psychology-2e/pages/8-1-how-memory-functions"),
    (["neuroscience", "brain", "cerebral cortex", "brain structure"],
     f"{_OPENSTAX_BASE}/psychology-2e/pages/3-4-the-brain-and-spinal-cord"),
    (["dopamine", "serotonin", "neurotransmitter system"],
     f"{_OPENSTAX_BASE}/psychology-2e/pages/3-2-cells-of-the-nervous-system"),
    (["psychopathology", "mental disorder", "dsm", "anxiety", "depression"],
     f"{_OPENSTAX_BASE}/psychology-2e/pages/15-1-what-are-psychological-disorders"),
]


# ---------------------------------------------------------------------------
# Cache directory
# ---------------------------------------------------------------------------

_LOCAL_CACHE = Path(__file__).parent.parent / "data" / "textbook_cache"
try:
    _LOCAL_CACHE.mkdir(parents=True, exist_ok=True)
    _CACHE_DIR = _LOCAL_CACHE
except OSError:
    _CACHE_DIR = Path("/tmp/textbook_cache")

_MANIFEST_PATH = _CACHE_DIR / "manifest.json"
_CACHE_MAX_AGE_DAYS = 90


def _ensure_cache_dir():
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _load_manifest() -> dict:
    if _MANIFEST_PATH.exists():
        return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    return {}


def _save_manifest(manifest: dict):
    _ensure_cache_dir()
    _MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _is_cache_fresh(entry: dict) -> bool:
    import datetime
    fetched = entry.get("fetched_at", "")
    if not fetched:
        return False
    try:
        dt = datetime.datetime.fromisoformat(fetched)
        age = datetime.datetime.now(datetime.timezone.utc) - dt
        return age.days < _CACHE_MAX_AGE_DAYS
    except Exception:
        return False


def get_cached(url: str) -> str | None:
    manifest = _load_manifest()
    h = _url_hash(url)
    entry = manifest.get(h)
    if not entry or not _is_cache_fresh(entry):
        return None
    cache_file = _CACHE_DIR / f"{h}.txt"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")
    return None


def store_cache(url: str, text: str, source_type: str):
    import datetime
    _ensure_cache_dir()
    h = _url_hash(url)
    cache_file = _CACHE_DIR / f"{h}.txt"
    cache_file.write_text(text, encoding="utf-8")
    manifest = _load_manifest()
    manifest[h] = {
        "url": url,
        "source_type": source_type,
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "chars": len(text),
    }
    _save_manifest(manifest)


# ---------------------------------------------------------------------------
# URL fetching + text extraction
# ---------------------------------------------------------------------------

def _fetch_and_extract(url: str, max_chars: int = 5000) -> str | None:
    """Fetch a URL and extract readable text content."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode("utf-8")
    except Exception as e:
        print(f"    Failed to fetch {url}: {e}")
        return None

    # Detect JS-only pages
    if "you must enable javascript" in html.lower() or len(html) < 500:
        print(f"    Page requires JavaScript, trying content API...")
        cnx_match = re.search(r"/books/([^/]+)/pages/(.+?)(?:\?|$)", url)
        if cnx_match:
            book_slug, page_slug = cnx_match.groups()
            api_url = f"https://openstax.org/apps/archive/20250305.212154/contents/{book_slug}:{page_slug}.json"
            try:
                req2 = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
                resp2 = urllib.request.urlopen(req2, timeout=15)
                data = json.loads(resp2.read().decode("utf-8"))
                html = data.get("content", "")
                if not html:
                    return None
            except Exception:
                return None

    # Strip scripts and styles
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    # Find content start markers
    for marker in ["Learning Objectives", "By the end of this section", "Introduction"]:
        start = text.find(marker)
        if start > 0:
            text = text[start:]
            break

    chapter_text = text[:max_chars].strip()
    if not chapter_text or len(chapter_text) < 200:
        return None
    return chapter_text


# ---------------------------------------------------------------------------
# Keyword matching against the index
# ---------------------------------------------------------------------------

def _match_topic_to_index(topic_name: str) -> str | None:
    """Match a topic name against the OpenStax index using keyword overlap.

    Returns the best matching URL or None.
    """
    topic_lower = topic_name.lower()
    topic_words = set(topic_lower.split())

    best_url = None
    best_score = 0

    for keywords, url in OPENSTAX_INDEX:
        score = 0
        for kw in keywords:
            kw_lower = kw.lower()
            # Exact substring match in topic name (highest weight)
            if kw_lower in topic_lower:
                score += 3
            # Any keyword word appears in topic words
            elif any(w in topic_words for w in kw_lower.split()):
                score += 1

        if score > best_score:
            best_score = score
            best_url = url

    # Require at least a reasonable match
    if best_score >= 2:
        return best_url
    return None


def _flash_pick_chapter(topic_name: str) -> str | None:
    """Use Flash to pick the best chapter from the index when keyword matching fails."""
    from google import genai

    # Build a numbered list of chapters
    chapters = []
    for i, (keywords, url) in enumerate(OPENSTAX_INDEX):
        slug = url.split("/pages/")[-1] if "/pages/" in url else url
        chapters.append(f"{i+1}. {', '.join(keywords[:3])} → {slug}")

    prompt = (
        f"Topic: \"{topic_name}\"\n\n"
        f"Which chapter number is most relevant? Pick ONE number from the list below.\n"
        f"If none are relevant, say 0.\n\n"
        + "\n".join(chapters)
    )

    try:
        client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)
        response = client.models.generate_content(
            model=CHUNKER_FALLBACK_MODEL,
            contents=prompt,
            config={"temperature": 0.0, "max_output_tokens": 10},
        )
        text = (response.text or "").strip()
        # Extract number
        match = re.search(r"\d+", text)
        if match:
            idx = int(match.group()) - 1
            if 0 <= idx < len(OPENSTAX_INDEX):
                return OPENSTAX_INDEX[idx][1]
    except Exception as e:
        print(f"    Flash chapter pick failed: {e}")

    return None


# ---------------------------------------------------------------------------
# NCBI Bookshelf fallback
# ---------------------------------------------------------------------------

def _search_ncbi_bookshelf(topic_name: str) -> dict | None:
    """Search NCBI Bookshelf for a free textbook chapter."""
    try:
        query = urllib.parse.quote(f"{topic_name} AND free full text[filter]")
        search_url = (
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            f"?db=books&term={query}&retmax=1&retmode=json"
        )
        req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode("utf-8"))
        ids = data.get("esearchresult", {}).get("idlist", [])
        if not ids:
            return None
        book_id = ids[0]
        url = f"https://www.ncbi.nlm.nih.gov/books/NBK{book_id}/"
        return {"url": url, "source_type": "ncbi_bookshelf"}
    except Exception as e:
        print(f"    NCBI search failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def search_textbook(topic_name: str) -> dict:
    """Find and fetch relevant textbook content for a topic.

    Returns:
        - text: str | None — chapter text (up to 5000 chars)
        - url: str | None — source URL
        - source_type: "openstax" | "ncbi_bookshelf" | "none"
    """
    result = {"text": None, "url": None, "source_type": "none"}

    print(f"    Searching textbook for '{topic_name}'...")

    # Tier 1: Keyword match against OpenStax index (free, instant)
    url = _match_topic_to_index(topic_name)

    # Tier 2: Flash picks from the index (cheap, ~200 tokens)
    if not url:
        url = _flash_pick_chapter(topic_name)

    # Fetch OpenStax content
    if url:
        cached = get_cached(url)
        if cached:
            print(f"    Textbook (cached): {url[:60]}...")
            return {"text": cached, "url": url, "source_type": "openstax"}

        text = _fetch_and_extract(url)
        if text:
            store_cache(url, text, "openstax")
            print(f"    Textbook (fetched): {url[:60]}... ({len(text)} chars)")
            return {"text": text, "url": url, "source_type": "openstax"}

    # Tier 3: NCBI Bookshelf
    time.sleep(0.5)
    ncbi = _search_ncbi_bookshelf(topic_name)
    if ncbi:
        ncbi_url = ncbi["url"]
        cached = get_cached(ncbi_url)
        if cached:
            print(f"    Textbook (cached, NCBI): {ncbi_url[:60]}...")
            return {"text": cached, "url": ncbi_url, "source_type": "ncbi_bookshelf"}

        text = _fetch_and_extract(ncbi_url)
        if text:
            store_cache(ncbi_url, text, "ncbi_bookshelf")
            print(f"    Textbook (fetched, NCBI): {ncbi_url[:60]}... ({len(text)} chars)")
            return {"text": text, "url": ncbi_url, "source_type": "ncbi_bookshelf"}

    print(f"    No textbook found for '{topic_name}'")
    return result
