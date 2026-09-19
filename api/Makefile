.PHONY: help install bootstrap-admin start worker test test-unit guards lint typecheck arch ci db-up db-down migrate migrate-down new-migration openapi format engine-dev status status-check data-model

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
	@echo "  make engine-dev  install osce_assessment from the local checkout, editable"
	@echo "  make bootstrap-admin EMAIL=you@example.com   make the first platform admin"
	@echo "  make status      regenerate the evidence half of docs/STATUS.md"
	@echo "  make seed-platform  author the four consumer exams and rubrics (dry run)"
	@echo "  make data-model  check docs/DATA-MODEL.md against the schema"

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
	poetry run python scripts/check_data_model.py

ci: lint typecheck arch guards test status-check

openapi:
	poetry run python scripts/export_openapi.py

# The engine is a dependency, not a vendored subtree (ADR 0009, E-1). For local
# work install it from the sibling checkout so a change there is visible here
# without a tag and a reinstall. Deployments pin the tag instead.
ENGINE ?= ../../assessment-platform/packages/osce_assessment

NAME ?= Platform Admin

bootstrap-admin:
	@test -n "$(EMAIL)" || { echo "Set EMAIL=you@example.com"; exit 1; }
	poetry run python scripts/bootstrap_admin.py --email "$(EMAIL)" --name "$(NAME)"

grant-exam-access:
	@test -n "$(EMAIL)" || { echo "Set EMAIL=you@example.com"; exit 1; }
	poetry run python scripts/grant_exam_access.py --email "$(EMAIL)" --exam "$(or $(EXAM),sca)"

engine-dev:
	@test -f "$(ENGINE)/pyproject.toml" || 		{ echo "No engine at $(ENGINE). Set ENGINE=<path to packages/osce_assessment>."; exit 1; }
	poetry run pip install -e "$(ENGINE)"
	poetry run python -c "import osce_assessment as e; print('osce_assessment', e.__version__)"

# STATUS.md drifted from the code badly enough that slices were described as
# complete while their rules had no caller. The generated half is derived, and
# `status-check` fails when it no longer matches.
# A migrated database has no exams and no rubrics (ADR 0016), so nothing can
# be run in it until the platform catalogue is authored. Idempotent: an exam
# that already exists is left exactly as it is.
seed-platform:
	poetry run python scripts/seed_platform.py --dry-run
	@echo "That was a dry run. Re-run with: poetry run python scripts/seed_platform.py"

generate-seed:
	poetry run python scripts/generate_platform_seed.py

status:
	poetry run python scripts/status_report.py --write

status-check:
	poetry run python scripts/status_report.py --check

# The schema reference is checked like the slice READMEs are: a document
# nothing verifies is the failure `docs/STATUS.md` exists to remember.
data-model:
	poetry run python scripts/check_data_model.py
