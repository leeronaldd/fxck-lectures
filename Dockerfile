FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the pipeline source code (src/) and backend app
COPY src/ ./src/
COPY backend/app/ ./app/
COPY data/ ./data/
COPY docs/reference/ ./docs/reference/

# Set env vars
ENV PYTHONUNBUFFERED=1

# Cloud Run uses PORT env var (default 8080)
# Hypercorn supports HTTP/2, removing Cloud Run's 32MB body limit for HTTP/1.1
CMD ["hypercorn", "app.main:app", "--bind", "0.0.0.0:8080"]
