# syntax=docker/dockerfile:1

# ========== STAGE 1: Build Angular SPA for Docker ==========
FROM node:20-alpine AS angular-builder

WORKDIR /app

COPY edysync/package*.json edysync/
RUN cd edysync && npm ci --legacy-peer-deps

COPY edysync/ edysync/
RUN cd edysync && npx ng build --configuration=docker

# ========== STAGE 2: Python dependencies ==========
FROM python:3.11-slim AS python-builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ========== STAGE 3: Final image ==========
FROM python:3.11-slim
LABEL maintainer="Moscowle Team" \
      description="Moscowle IA - Plataforma de salud mental con IA"

WORKDIR /app

# Create non-root user
RUN groupadd --system --gid 1001 app && \
    useradd --system --no-log-init --uid 1001 --gid app app

# Install runtime system dependencies
# nginx is kept intentionally — required for serving the SPA and proxying
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    tesseract-ocr \
    tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=python-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-builder /usr/local/bin /usr/local/bin

# Copy pre-built Angular SPA
COPY --from=angular-builder /app/edysync/dist/edysync/browser/ /usr/share/nginx/html/

# Copy entrypoint and nginx config
COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
RUN chmod +x /entrypoint.sh

# Copy application code
COPY --chown=app:app . .

# Create runtime directories
RUN mkdir -p /app/backups /app/logs /app/uploads /app/instance && \
    chown -R app:app /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_ENV=production

EXPOSE 80

USER app

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:80/api/health')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--worker-class", "eventlet", "--workers", "1", "--bind", "0.0.0.0:8080", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "server:application"]
