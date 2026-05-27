FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN mkdir -p /app/backups && pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "-k", "eventlet", "-w", "1", "wsgi_entry:application"]
