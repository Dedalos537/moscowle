.PHONY: install test lint format dev docker-build docker-up clean

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

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f backend

migrate:
	flask db upgrade

migrate-create:
	flask db migrate -m "$(msg)"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage coverage_report .pytest_cache
