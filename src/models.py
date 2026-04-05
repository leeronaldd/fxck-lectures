from pydantic import BaseModel


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
