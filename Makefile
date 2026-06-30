.PHONY: dev lint test reply

dev:
	pip install -e ".[dev]"

lint:
	ruff check openclaw tests

test:
	pytest -q

reply:
	openclaw --message "How do I reset my password?"
