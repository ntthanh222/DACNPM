# CyberSec Assistant Platform - Backend Dockerfile
# Multi-stage build for optimized production image

# ============================================
# Stage 1: Builder
# ============================================
FROM python:3.11-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /build

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --user --upgrade pip && \
    pip install --user -r requirements.txt

# ============================================
# Stage 2: Runtime
# ============================================
FROM python:3.11-slim AS runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Copy Python packages from builder to system-wide location (accessible by all users)
COPY --from=builder /root/.local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /root/.local/bin /usr/local/bin

# Copy application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Create necessary directories
RUN mkdir -p /app/logs /app/tmp && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Start application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# ============================================
# Stage 3: Development
# ============================================
FROM runtime AS development

# Switch back to root to install dev dependencies
USER root

# Install development dependencies (system-wide, accessible by all users)
RUN pip install pytest pytest-asyncio pytest-cov black flake8 pylint mypy

# Copy test files
COPY backend/tests/ /app/backend/tests/

# Fix ownership for appuser
RUN chown -R appuser:appuser /app/backend/tests /app

# Switch back to non-root user
USER appuser

ENV PYTHONPATH=/app

# Override CMD for development
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]

# ============================================
# Stage 4: Rasa Action Server (Python 3.10)
# ============================================
# Rasa SDK 3.6.2 supports Python 3.8-3.10 only. Keep this image independent
# from the backend Python 3.11 Docker image and the local Python 3.14 venv.
FROM python:3.10-slim AS actions

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

COPY backend/requirements-actions.txt /tmp/requirements-actions.txt
RUN pip install --upgrade pip && \
    pip install -r /tmp/requirements-actions.txt && \
    pip install --no-deps \
      rasa-sdk==3.6.2 \
      supabase==2.31.0 \
      postgrest==2.31.0 \
      realtime==2.31.0 \
      storage3==2.31.0 \
      supabase-auth==2.31.0 \
      supabase-functions==2.31.0 \
      google-auth==2.55.2 \
      google-genai==2.10.0

COPY backend/ ./backend/

RUN mkdir -p /app/logs && chown -R appuser:appuser /app

USER appuser

EXPOSE 5055

CMD ["python", "-m", "rasa_sdk.__main__", "--actions", "backend.rasa_actions.actions", "--port", "5055"]
