# Multi-stage build for minimal Streamlit image
# Stage 1: Builder - install dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for faster dependency resolution and installation
RUN pip install --no-cache-dir uv

# Copy only dependency files first (better layer caching)
COPY pyproject.toml ./

# Install dependencies to a virtual environment
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache .

# Stage 2: Runtime - minimal final image
FROM python:3.12-slim

WORKDIR /app

# Install only runtime essentials (curl for healthcheck)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY . .

# Set PATH to use virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN useradd -m -u 1000 streamlit && \
    chown -R streamlit:streamlit /app
USER streamlit

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
