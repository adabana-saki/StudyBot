# =============================================================================
# Stage 1: Builder - install Python dependencies
# =============================================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build-time dependencies needed to compile native extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install all Python packages into a virtual environment for clean copying
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 2: Runtime - minimal image with only runtime dependencies
# =============================================================================
FROM python:3.12-slim AS runtime

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# Install only runtime system libraries (no compilers, no -dev packages)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 fonts-noto-cjk && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the pre-built virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app
USER botuser

CMD ["python", "-u", "main.py"]
