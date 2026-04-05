"""Configuration for the lecture replacement tool."""

import os

# Google Cloud / Vertex AI settings (using google-genai SDK with vertexai=True)
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "project-bc1fc31b-94c5-44b0-904")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "global")

# Model selection per stage
CHUNKER_FALLBACK_MODEL = "gemini-3-flash-preview"  # cheap, fast — only used when regex fails
GENERATOR_MODEL = "gemini-3-flash-preview"          # quality matters for explanation generation
EVALUATOR_MODEL = "gemini-3-flash-preview"          # quality matters for evaluation

# Paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
TRANSCRIPTS_DIR = os.path.join(DATA_DIR, "transcripts")
OUTPUT_DIR = os.path.join(DATA_DIR, "output")
