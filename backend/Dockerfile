# syntax=docker/dockerfile:1

# --- Base image -------------------------------------------------------------
# Slim Python (3.12 has wheels for every dependency; avoids source builds).
FROM python:3.12-slim AS runtime

# Faster, cleaner Python in containers.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# --- Dependencies (cached layer) --------------------------------------------
# Copy only requirements first so the pip layer is reused when app code changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# --- Application code --------------------------------------------------------
COPY app ./app

# --- Run as a non-root user --------------------------------------------------
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# --- Network -----------------------------------------------------------------
EXPOSE 8000

# --- Healthcheck -------------------------------------------------------------
# Hits the app's /health endpoint. slim has no curl, so use Python's urllib.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

# --- Start -------------------------------------------------------------------
# Multiple workers for production. Credentials/config come from the runtime
# environment (docker compose --env-file / IAM role) — never baked into the image.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
