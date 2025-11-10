# Backend Dockerfile - FastAPI
FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Install OS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    default-mysql-client \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements if exist, else try to generate from poetry/pyproject (best-effort)
COPY ./requirements.txt /app/requirements.txt
RUN if [ -f /app/requirements.txt ]; then pip install --no-cache-dir -r /app/requirements.txt; fi

# Copy app
COPY . /app

# Copy entrypoint / wait scripts (if they exist in the build context)
COPY ./wait-for-db_init.sh /app/wait-for-db_init.sh
COPY ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/wait-for-db_init.sh /app/entrypoint.sh || true

# Expose port
EXPOSE 8001

# Use entrypoint wrapper to wait for DB init then start the app
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["/usr/local/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
