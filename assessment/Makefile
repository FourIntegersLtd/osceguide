.PHONY: install test lint-leakage engine-branch

install:
	poetry install

test:
	poetry run pytest -q

# The consumer-context guard: fails if engine code mentions any consumer identity.
lint-leakage:
	poetry run pytest -q tests/test_no_consumer_leakage.py

# Refresh the `engine` branch: the contents of packages/osce_assessment as a
# standalone history, which the backends vendor with `git subtree`. Run after
# every change to the engine that consumers should be able to pull.
engine-branch:
	git subtree split --prefix=packages/osce_assessment -b engine
	@echo "engine branch now at $$(git rev-parse --short engine)"

# --- Running the workers -----------------------------------------------------
# Railway / K8s container: gunicorn on PATH, deps baked in. Local: poetry run.
PORT ?= 8080
export OSCE_LIVEKIT_WORKER ?= assessment
IS_CONTAINER_HOST := $(filter $(OSCE_LIVEKIT_HOSTING),self-hosted)
ifneq ($(RAILWAY_PROJECT_ID)$(RAILWAY_ENVIRONMENT)$(IS_CONTAINER_HOST),)
RUN :=
START_PREREQS :=
else
RUN := poetry run
START_PREREQS := install download-files
endif
export PYTHONPATH := $(CURDIR):$(CURDIR)/packages$(if $(PYTHONPATH),:$(PYTHONPATH),)

.PHONY: download-files start start-assessment dev-assessment stop

download-files:
	$(RUN) python -m livekit.agents download-files

## gunicorn /health + one supervised worker subprocess (OSCE_LIVEKIT_WORKER)
start: $(START_PREREQS)
	$(RUN) gunicorn hosting.supervisor:application --bind 0.0.0.0:$(PORT) \
		--workers 1 --threads 2 --worker-class gthread --timeout 300 --keep-alive 5 --graceful-timeout 30

start-assessment:
	OSCE_LIVEKIT_WORKER=assessment $(MAKE) start

## the assessment worker alone, in dev mode (no supervisor)
dev-assessment: install
	poetry run python -m livekit_assessment_worker.entrypoint dev

stop:
	@pkill -f "gunicorn.*hosting.supervisor:application" 2>/dev/null || true
	@pkill -f "livekit_assessment_worker.entrypoint" 2>/dev/null || true
