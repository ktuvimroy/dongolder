FROM python:3.11-slim

# Build tools needed for wheel compilation (numpy, pandas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python package (hatchling src layout: reads pyproject.toml directly)
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Download TextBlob/NLTK corpora at build time so the container is self-contained
RUN python -m textblob.download_corpora

# Persistent data directory (mount a volume here in production)
RUN mkdir -p /data

# For multi-arch builds (Oracle Cloud ARM64):
#   docker buildx build --platform linux/amd64,linux/arm64 -t gold-signal-bot .

CMD python -m gold_signal_bot
