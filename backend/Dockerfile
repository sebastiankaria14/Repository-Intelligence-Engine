# ─────────────────────────────────────────────────
# RIE Backend — Dockerfile
# ─────────────────────────────────────────────────
FROM python:3.11-slim AS base

# System deps for git, tree-sitter, and native builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libgit2-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for cloned repos
RUN mkdir -p /app/repos

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
