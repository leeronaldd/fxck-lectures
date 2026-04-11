FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Download model weights at build time (no GPU needed for download)
# This bakes the ~1.5GB model into the image so cold starts are fast
# Small model — fast enough, pipeline corrects misspellings via textbook RAG
RUN python3 -c "from huggingface_hub import snapshot_download; snapshot_download('Systran/faster-whisper-small')"

COPY main.py .

ENV PYTHONUNBUFFERED=1

CMD ["hypercorn", "main:app", "--bind", "0.0.0.0:8080"]
