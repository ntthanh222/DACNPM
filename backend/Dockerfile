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
COPY requirements.txt .
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
COPY . .

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
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# ============================================
# Stage 3: Development
# ============================================
FROM runtime AS development

# Switch back to root to install dev dependencies
USER root

# Install development dependencies (system-wide, accessible by all users)
RUN pip install pytest pytest-asyncio pytest-cov black flake8 pylint mypy

# Create a symlink so absolute imports like `backend.database.connection`
# resolve to /app during development. main.py adds parent.parent to sys.path,
# expecting `backend` to be importable; this mirrors that locally.
RUN ln -s /app /backend

# Copy test files
COPY tests/ /app/tests/

# Fix ownership for appuser
RUN chown -R appuser:appuser /app/tests /app

# Switch back to non-root user
USER appuser

# Make the parent of /app (/) importable so `backend.*` resolves via the symlink
ENV PYTHONPATH=/

# Override CMD for development
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]
