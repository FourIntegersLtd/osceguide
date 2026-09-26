.PHONY: install test lint-leakage

install:
	poetry install

test:
	poetry run pytest -q

# The consumer-context guard: fails if engine code mentions any consumer identity.
lint-leakage:
	poetry run pytest -q tests/test_no_consumer_leakage.py

# --- Running the workers locally ----------------------------------------------
# Containers do not use make: the Dockerfile starts the worker directly, so the
# platform's stop signal reaches it (see hosting/run_worker.py).
export OSCE_LIVEKIT_WORKER ?= assessment
export PYTHONPATH := $(CURDIR):$(CURDIR)/packages$(if $(PYTHONPATH),:$(PYTHONPATH),)

.PHONY: download-files start start-assessment start-assistant dev-assessment dev-assistant stop

download-files:
	poetry run python -m livekit.agents download-files

## the worker named by OSCE_LIVEKIT_WORKER, exactly as the container runs it
start: install download-files
	poetry run python -m hosting.run_worker start

start-assessment:
	OSCE_LIVEKIT_WORKER=assessment $(MAKE) start

start-assistant:
	OSCE_LIVEKIT_WORKER=assistant $(MAKE) start

## one worker in dev mode (reloads on code changes)
dev-assessment: install
	poetry run python -m livekit_assessment_worker.entrypoint dev

dev-assistant: install
	poetry run python -m livekit_assistant_worker.entrypoint dev

## SIGTERM, so each worker drains its sessions before it exits
stop:
	@pkill -f "hosting.run_worker" 2>/dev/null || true
	@pkill -f "livekit_assessment_worker.entrypoint" 2>/dev/null || true
	@pkill -f "livekit_assistant_worker.entrypoint" 2>/dev/null || true
