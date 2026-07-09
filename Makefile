.PHONY: install test lint format dev dev-docker dev-docker-up dev-docker-down \
        dev-docker-logs dev-docker-db docker-build docker-up docker-down docker-logs \
        migrate migrate-create clean

# ─── Local development (no Docker) ──────────────────────────────────────────

install:
	pip install -r requirements.txt
	pre-commit install

test:
	python -m pytest tests/ --tb=short -q

test-cov:
	python -m pytest tests/ --cov=app --cov-report=term-missing

lint:
	ruff check app/

lint-fix:
	ruff check --fix app/

format:
	ruff format app/

format-check:
	ruff format --check app/

dev:
	python run.py

# ─── Docker development (uses docker-compose.dev.yml) ──────────────────────

dev-docker:
	docker compose -f docker-compose.dev.yml up --watch

dev-docker-build:
	docker compose -f docker-compose.dev.yml build

dev-docker-up:
	docker compose -f docker-compose.dev.yml up -d

dev-docker-down:
	docker compose -f docker-compose.dev.yml down

dev-docker-logs:
	docker compose -f docker-compose.dev.yml logs -f

dev-docker-db:
	docker compose -f docker-compose.dev.yml exec db psql -U moscowle

# ─── Docker production (uses docker-compose.yml) ───────────────────────────

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

# ─── Database ──────────────────────────────────────────────────────────────

migrate:
	flask db upgrade

migrate-create:
	flask db migrate -m "$(msg)"

# ─── Cleanup ───────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage coverage_report .pytest_cache
