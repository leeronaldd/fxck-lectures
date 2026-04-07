"""Configuration for the lecture replacement tool."""

import os

# Google Cloud / Vertex AI settings (using google-genai SDK with vertexai=True)
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "project-bc1fc31b-94c5-44b0-904")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "global")

# Groq API settings (for Whisper STT)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
TRANSCRIPTION_MODEL = "whisper-large-v3-turbo"  # $0.04/hr — cheapest available on Groq (distil was deprecated Aug 2025)

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
SCREENSHOTS_DIR = os.path.join(DATA_DIR, "screenshots")
