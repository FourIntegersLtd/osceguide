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
