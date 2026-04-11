FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Download the model at build time so it's baked into the image
# (no download delay on cold start)
RUN python3 -c "from faster_whisper import WhisperModel; WhisperModel('large-v3-turbo', device='cuda', compute_type='float16')"

COPY main.py .

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
