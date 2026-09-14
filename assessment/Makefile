.PHONY: install test lint-leakage

install:
	poetry install

test:
	poetry run pytest -q

# The consumer-context guard: fails if engine code mentions any consumer identity.
lint-leakage:
	poetry run pytest -q tests/test_no_consumer_leakage.py
