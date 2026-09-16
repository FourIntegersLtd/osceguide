.PHONY: help install start worker test test-unit guards lint typecheck arch ci db-up db-down migrate migrate-remote new-migration openapi format

help:
	@echo "OSCE Guide Platform API"
	@echo ""
	@echo "  make install     poetry install"
	@echo "  make db-up       start local Postgres + Redis (docker compose)"
	@echo "  make migrate     apply supabase/migrations/ to DATABASE_URL (local)"
	@echo "  make migrate-remote  supabase db push (linked project)"
	@echo "  make new-migration M=add_exams   create an empty timestamped migration file"
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
	poetry run python -m app.core.migrations

migrate-remote:
	supabase db push

new-migration:
	@test -n "$(M)" || (echo "M=name is required"; exit 1)
	@f=supabase/migrations/$$(date -u +%Y%m%d%H%M%S)_$(M).sql; printf -- '-- $(M)\n' > $$f; echo "created $$f"

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
