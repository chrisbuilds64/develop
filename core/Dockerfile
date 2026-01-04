# Tweight Core API - Production Dockerfile
# Multi-stage build for smaller image size

# Stage 1: Build stage
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY main.py .
COPY database.py .
COPY models.py .
COPY schemas.py .

# UC-003: Copy auth module
COPY auth/ ./auth/

# UC-003: Copy alembic migrations
COPY alembic/ ./alembic/
COPY alembic.ini .

# UC-003: Copy environment config (will be overridden by docker-compose)
COPY .env.example .env

# UC-003: Copy entrypoint script for migrations
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Create directory for SQLite database
RUN mkdir -p /app/data

# Expose port 8000
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run migrations and start application
ENTRYPOINT ["/app/docker-entrypoint.sh"]
