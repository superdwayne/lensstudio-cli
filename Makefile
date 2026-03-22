.PHONY: install dev test lint format typecheck all

install:
	pip install -r requirements.txt
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest --cov=cli_anything --tb=short -v

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy cli_anything/

all: install dev lint typecheck test
