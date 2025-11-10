# Backend Dockerfile - FastAPI
FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Install OS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements if exist, else try to generate from poetry/pyproject (best-effort)
COPY ./requirements.txt /app/requirements.txt
RUN if [ -f /app/requirements.txt ]; then pip install --no-cache-dir -r /app/requirements.txt; fi

# Copy app
COPY . /app

# Expose port
EXPOSE 8001

# Default command
CMD ["/usr/local/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
