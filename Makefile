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
	python start_server.py

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
