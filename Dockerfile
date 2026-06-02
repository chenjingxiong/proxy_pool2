FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose API port
EXPOSE 5010

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5010/count/')" || exit 1

# Start with gunicorn via the project entry point
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5010", \
     "--workers", "4", \
     "--access-logfile", "-", \
     "--access-logformat", "%(h)s %(l)s %(t)s \"%(r)s\" %(s)s \"%(a)s\"", \
     "api.proxyApi:app"]
