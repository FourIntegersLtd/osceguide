.PHONY: help install bootstrap-admin start worker test test-unit guards lint typecheck arch ci db-up db-down migrate migrate-down new-migration openapi format data-model product-guide

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
	@echo "  make bootstrap-admin EMAIL=you@example.com   make the first platform admin"
	@echo "  make seed-platform  author the four consumer exams and rubrics (dry run)"
	@echo "  make data-model  check docs/DATA-MODEL.md and the field guide's schema"
	@echo "  make product-guide  check the product guide covers every refusal code"

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
	poetry run pytest -q -n auto

test-unit:
	poetry run pytest -q -n auto tests/unit

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
	poetry run python scripts/check_data_model.py

ci: lint typecheck arch guards test

openapi:
	poetry run python scripts/export_openapi.py

NAME ?= Platform Admin

bootstrap-admin:
	@test -n "$(EMAIL)" || { echo "Set EMAIL=you@example.com"; exit 1; }
	poetry run python scripts/bootstrap_admin.py --email "$(EMAIL)" --name "$(NAME)"

grant-exam-access:
	@test -n "$(EMAIL)" || { echo "Set EMAIL=you@example.com"; exit 1; }
	poetry run python scripts/grant_exam_access.py --email "$(EMAIL)" --exam "$(or $(EXAM),sca)"

# A migrated database has no exams and no rubrics (ADR 0016), so nothing can
# be run in it until the platform catalogue is authored. Idempotent: an exam
# that already exists is left exactly as it is.
seed-platform:
	poetry run python scripts/seed_platform.py --dry-run
	@echo "That was a dry run. Re-run with: poetry run python scripts/seed_platform.py"

generate-seed:
	poetry run python scripts/generate_platform_seed.py

# The schema reference is checked like the slice READMEs are: a document
# nothing verifies drifts from the code it describes.
data-model:
	poetry run python scripts/check_data_model.py
	PYTHONPATH=. poetry run python scripts/build_field_guide.py --check

# The product guide's "what can go wrong" rows carry data-code attributes; every
# refusal the api can answer with must have one, and none may cite a dead code.
product-guide:
	PYTHONPATH=. poetry run python scripts/build_product_guide.py --check
