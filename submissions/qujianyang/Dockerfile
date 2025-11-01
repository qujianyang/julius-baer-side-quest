# Modern Banking Client - Dockerfile
# Gold Level Feature: Containerization (DevOps)

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY banking_client.py .
COPY config.py .
COPY banking_cli.py .

# Make CLI executable
RUN chmod +x banking_cli.py

# Health check (ping the API)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://host.docker.internal:8123/accounts', timeout=5)" || exit 1

# Default command - show help
ENTRYPOINT ["python", "banking_cli.py"]
CMD ["--help"]

# Usage examples:
# Build: docker build -t banking-client .
# Run demo: docker run --network host banking-client demo
# Transfer: docker run --network host banking-client transfer --from ACC1000 --to ACC1001 --amount 100
# With auth: docker run --network host banking-client transfer --from ACC1000 --to ACC1001 --amount 100 --auth
