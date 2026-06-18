# ========== STAGE 1: Build Angular SPA ==========
FROM node:20-alpine AS angular-builder

WORKDIR /app

COPY edysync/package*.json edysync/
RUN cd edysync && npm ci --legacy-peer-deps

COPY edysync/ edysync/
RUN cd edysync && npx ng build --configuration=production

# ========== STAGE 2: Python dependencies ==========
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ========== STAGE 3: Final image ==========
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-spa && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    addgroup --system --gid 1001 app && \
    adduser --system --uid 1001 app && \
    mkdir -p /app/backups /app/logs /app/uploads /app/instance && \
    chown -R app:app /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --chown=app:app . .

# Copy pre-built Angular SPA from stage 1
COPY --from=angular-builder /app/edysync/dist/edysync/browser/ /app/edysync/dist/edysync/browser/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_ENV=production

EXPOSE 8080

USER app

HEALTHCHECK --interval=30s --timeout=10s --retries=5 \
    CMD python -c "import urllib.request, os; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", \"8080\")}/api/health')" || exit 1

CMD ["python", "run_gunicorn.py"]
