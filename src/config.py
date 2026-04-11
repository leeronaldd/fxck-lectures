"""Configuration for the lecture replacement tool."""

import os

# Google Cloud / Vertex AI settings (using google-genai SDK with vertexai=True)
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "project-bc1fc31b-94c5-44b0-904")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "global")

# Transcription now uses Gemini Flash (no separate STT API needed)
# Groq API key kept for backward compat but no longer required
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
TRANSCRIPTION_MODEL = "gemini-3-flash-preview"  # Gemini Flash multimodal audio — no rate limits

# Model selection per stage — configurable via env vars
# To switch cheap model to DeepSeek V3.2 ($0.28/$0.42 vs Flash $0.50/$3.00):
#   1. Enable DeepSeek V3.2 in Vertex AI Model Garden console
#   2. Set env var: CHEAP_MODEL=deepseek-v3-2
#   3. May need: GCP_LOCATION=us-central1
CHUNKER_FALLBACK_MODEL = os.environ.get("CHEAP_MODEL", "gemini-3-flash-preview")
GENERATOR_MODEL = os.environ.get("GENERATOR_MODEL", "gemini-3.1-pro-preview")
EVALUATOR_MODEL = os.environ.get("EVALUATOR_MODEL", "gemini-3.1-pro-preview")

# Paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
TRANSCRIPTS_DIR = os.path.join(DATA_DIR, "transcripts")
OUTPUT_DIR = os.path.join(DATA_DIR, "output")
SCREENSHOTS_DIR = os.path.join(DATA_DIR, "output", "screenshots")
