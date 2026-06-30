.PHONY: install dev lint fmt test demo

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

lint:
	ruff check openclaw tests

fmt:
	ruff check --fix openclaw tests

test:
	pytest -q

demo:
	openclaw demo
