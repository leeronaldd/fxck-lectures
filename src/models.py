from pydantic import BaseModel
from datetime import datetime


class EmphasisSignal(BaseModel):
    keyword: str        # e.g., "important", "make sure you know"
    context: str        # the surrounding sentence where this was found
    sentiment: str      # "positive" (study this) or "negative" (don't memorize this)


class Chunk(BaseModel):
    chunk_index: int
    topic_name: str
    transcript_text: str
    word_count: int
    emphasis_score: str                     # HIGH / MEDIUM / LOW
    emphasis_signals: list[EmphasisSignal]
    key_terms: list[str]                    # technical terms in this chunk
    prerequisites: list[str]               # terms from earlier chunks this depends on
    forward_references: list[str]          # terms used here but defined later
    reorder_suggestion: str | None = None  # e.g., "Move after chunk 5 (defines X)"
    needs_expansion: bool = False          # True if professor skimmed a complex topic
    expansion_hint: str | None = None      # e.g., "Covers 7 Baltimore classes in 1026 words — expand each class into its own explanation"
    is_sub_chunk: bool = False             # True if this was split from a larger chunk by LLM
    parent_topic: str | None = None        # Original chunk topic if this is a sub-chunk


class Explanation(BaseModel):
    chunk_index: int
    topic_name: str
    explanation_text: str                   # tutor-quality markdown explanation
    word_count: int
    emphasis_score: str                     # carried from chunk (HIGH / MEDIUM / LOW)
    learning_guidance: str                  # resolved contradictory emphasis into clear directive
    key_terms_explained: list[str] = []
    prerequisites_referenced: list[str] = []
    ci_percent: int | None = None            # exam importance score (0-100)
    ci_reasoning: str = ""                   # why this CI% score
    screenshot_refs: list[str] = []          # screenshot filenames matched to this chunk
    was_expanded: bool = False               # True if needs_expansion chunk was handled
    was_skipped: bool = False
    skip_reason: str | None = None
    generation_model: str = ""
    generation_timestamp: str = ""


class Screenshot(BaseModel):
    screenshot_index: int
    timestamp_seconds: float
    timestamp_display: str          # "12:34"
    image_filename: str             # "screenshot_007.jpg"
    description: str                # from Gemini Flash multimodal
    matched_chunk_index: int        # which chunk this belongs to
    matched_chunk_topic: str


class SlideChunk(BaseModel):
    slide_index: int                        # 1-based (Slide 1, Slide 2, ...)
    slide_image: str                        # "screenshot_003.jpg"
    slide_description: str = ""             # Gemini Flash description of the slide
    timestamp_start: float                  # seconds
    timestamp_end: float                    # seconds (next slide's start)
    timestamp_display: str                  # "20:52 - 23:50"
    transcript_text: str                    # professor's words during this slide
    word_count: int
    topic_name: str = ""                    # auto-derived from slide description or transcript
    emphasis_score: str = "MEDIUM"          # HIGH / MEDIUM / LOW
    emphasis_signals: list[EmphasisSignal] = []
    key_terms: list[str] = []
    needs_sub_chunking: bool = False        # True if >800 words
    sub_chunks: list[dict] | None = None    # sub-chunk names/ranges if split


class CIScore(BaseModel):
    chunk_index: int
    topic_name: str
    ci_percent: int                         # 0-100: how likely to be assessed on exams
    ci_reasoning: str                       # 1-2 sentences explaining why
    depth_recommendation: str               # "deep", "standard", or "light"
    professor_emphasis: str                 # carried from chunk (HIGH / MEDIUM / LOW)
