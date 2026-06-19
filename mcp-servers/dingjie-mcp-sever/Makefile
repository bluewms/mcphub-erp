.PHONY: test lint format build clean

test:
	uv run pytest -v

lint:
	uv run ruff check .
	uv run mypy src

format:
	uv run ruff format .
	uv run ruff check --fix .

build:
	uv build

clean:
	rm -rf dist/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:
	uv run dingjie-erp-mcp

run-readonly:
	uv run dingjie-erp-mcp --mode readonly

run-sse:
	uv run dingjie-erp-mcp --transport sse --port 8080
