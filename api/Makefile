.PHONY: help install start worker test test-unit guards lint typecheck arch ci db-up db-down migrate migrate-down new-migration openapi format

help:
	@echo "OSCE Guide Platform API"
	@echo ""
	@echo "  make install     poetry install"
	@echo "  make db-up       start local Postgres + Redis (docker compose)"
	@echo "  make migrate     alembic upgrade head"
	@echo "  make migrate-down  alembic downgrade -1"
	@echo "  make new-migration M=add_exams   autogenerate a migration (review it)"
	@echo "  make start       run the API on :8002 with reload"
	@echo "  make worker      run the background job worker"
	@echo "  make test        full test suite (needs Postgres: docker or TEST_DATABASE_URL)"
	@echo "  make test-unit   pure unit tests only, no database"
	@echo "  make guards      architecture guard tests on their own"
	@echo "  make lint        ruff"
	@echo "  make typecheck   mypy"
	@echo "  make arch        import-linter architecture rules"
	@echo "  make ci          lint + typecheck + arch + test"
	@echo "  make openapi     write openapi.json"

install:
	poetry install

db-up:
	docker compose up -d

db-down:
	docker compose down

migrate:
	poetry run alembic upgrade head

migrate-down:
	poetry run alembic downgrade -1

new-migration:
	@test -n "$(M)" || (echo "M=name is required"; exit 1)
	poetry run alembic revision --autogenerate -m "$(M)"
	@echo "Review the generated file: autogenerate misses constraint and index changes."

start:
	poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8002

worker:
	poetry run python -m app.worker.main

test:
	poetry run pytest -q

test-unit:
	poetry run pytest -q tests/unit

guards:
	poetry run pytest -q tests/guards

lint:
	poetry run ruff check .
	poetry run ruff format --check .

format:
	poetry run ruff format .
	poetry run ruff check --fix .

typecheck:
	poetry run mypy app

arch:
	poetry run lint-imports
	poetry run python scripts/check_slice_readmes.py

ci: lint typecheck arch guards test

openapi:
	poetry run python scripts/export_openapi.py
