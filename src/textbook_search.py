"""Textbook search: dynamically find and cache relevant textbook content.

Uses Google Search grounding via Gemini Flash to find OpenStax chapters,
then falls back to NCBI Bookshelf. Caches fetched content on disk.
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
# Cache directory
# ---------------------------------------------------------------------------

# Try local data/ dir first, fall back to /tmp (writable on Cloud Run)
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
    """Check if a cache entry is still within TTL."""
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


# ---------------------------------------------------------------------------
# Cache operations
# ---------------------------------------------------------------------------

def get_cached(url: str) -> str | None:
    """Return cached chapter text for a URL, or None if not cached/expired."""
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
    """Store chapter text in cache."""
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

    # Detect JS-only pages (OpenStax uses React, returns empty without JS)
    if "you must enable javascript" in html.lower() or len(html) < 500:
        print(f"    Page requires JavaScript, trying content API...")
        # OpenStax has a content API — try fetching via their CNX API
        cnx_match = re.search(r"/books/([^/]+)/pages/(.+?)(?:\?|$)", url)
        if cnx_match:
            book_slug, page_slug = cnx_match.groups()
            api_url = f"https://openstax.org/apps/archive/20250305.212154/contents/{book_slug}:{page_slug}.json"
            try:
                req2 = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
                resp2 = urllib.request.urlopen(req2, timeout=15)
                data = json.loads(resp2.read().decode("utf-8"))
                # The API returns HTML content in the "content" field
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
    # Reject if too short (likely a JS-only page or error page)
    if not chapter_text or len(chapter_text) < 200:
        return None
    return chapter_text


# ---------------------------------------------------------------------------
# Search strategies
# ---------------------------------------------------------------------------

def _search_openstax_via_gemini(topic_name: str) -> dict | None:
    """Use Gemini Flash with Google Search grounding to find OpenStax chapter.

    Returns {"url": str, "source_type": "openstax"} or None.
    """
    from google import genai
    from google.genai.types import Tool, GoogleSearch

    client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)

    prompt = (
        f"Find the most relevant OpenStax textbook chapter for the topic: \"{topic_name}\"\n\n"
        f"Search for: site:openstax.org/books {topic_name}\n\n"
        f"Return ONLY the full URL of the most relevant OpenStax chapter page. "
        f"The URL must start with https://openstax.org/books/. "
        f"If you cannot find a relevant OpenStax page, respond with exactly: NONE"
    )

    try:
        response = client.models.generate_content(
            model=CHUNKER_FALLBACK_MODEL,
            contents=prompt,
            config={
                "temperature": 0.0,
                "max_output_tokens": 256,
                "tools": [Tool(google_search=GoogleSearch())],
            },
        )

        # response.text can be None when using Google Search grounding
        text = (response.text or "").strip()
        if not text:
            # Try extracting from candidates
            try:
                text = response.candidates[0].content.parts[0].text.strip()
            except (IndexError, AttributeError):
                return None

        if text == "NONE" or "NONE" in text:
            return None

        # Extract URL — must be a chapter page (contain /pages/), not a book landing page
        url_match = re.search(r"https://openstax\.org/books/[^/]+/pages/[^\s\"'<>]+", text)
        if url_match:
            url = url_match.group(0).rstrip(".")
            return {"url": url, "source_type": "openstax"}

    except Exception as e:
        print(f"    OpenStax search failed: {e}")

    return None


def _search_ncbi_bookshelf(topic_name: str) -> dict | None:
    """Search NCBI Bookshelf for a free textbook chapter.

    Returns {"url": str, "source_type": "ncbi_bookshelf"} or None.
    """
    try:
        # Use NCBI E-utilities search API
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

        # Build a bookshelf URL from the ID
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

    Returns a dict with:
        - text: str | None — the chapter text (up to 5000 chars)
        - url: str | None — the source URL
        - source_type: "openstax" | "ncbi_bookshelf" | "none"

    Tries OpenStax first (via Google Search grounding), then NCBI Bookshelf.
    Caches results for 90 days.
    """
    result = {"text": None, "url": None, "source_type": "none"}

    # Step 1: Search OpenStax via Gemini + Google Search
    print(f"    Searching textbook for '{topic_name}'...")
    openstax = _search_openstax_via_gemini(topic_name)

    if openstax:
        url = openstax["url"]

        # Check cache first
        cached = get_cached(url)
        if cached:
            print(f"    Textbook (cached): {url[:60]}...")
            return {"text": cached, "url": url, "source_type": "openstax"}

        # Fetch and cache
        text = _fetch_and_extract(url)
        if text:
            store_cache(url, text, "openstax")
            print(f"    Textbook (fetched): {url[:60]}... ({len(text)} chars)")
            return {"text": text, "url": url, "source_type": "openstax"}

    # Step 2: Try NCBI Bookshelf
    time.sleep(0.5)  # rate limit
    ncbi = _search_ncbi_bookshelf(topic_name)

    if ncbi:
        url = ncbi["url"]

        cached = get_cached(url)
        if cached:
            print(f"    Textbook (cached, NCBI): {url[:60]}...")
            return {"text": cached, "url": url, "source_type": "ncbi_bookshelf"}

        text = _fetch_and_extract(url)
        if text:
            store_cache(url, text, "ncbi_bookshelf")
            print(f"    Textbook (fetched, NCBI): {url[:60]}... ({len(text)} chars)")
            return {"text": text, "url": url, "source_type": "ncbi_bookshelf"}

    # Step 3: No textbook found
    print(f"    No textbook found for '{topic_name}'")
    return result
