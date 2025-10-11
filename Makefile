# Use Python 3.13 where the packages are installed
PYTHON := /opt/homebrew/bin/python3.13

.PHONY: help install test lint format clean build release bump-patch bump-minor bump-major

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install the package in development mode
	pip install -e .[dev]

test: ## Run tests
	$(PYTHON) -m pytest tests/ -v

lint: ## Run linting
	# Stop the build if there are Python syntax errors or undefined names
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	# Exit-zero treats all errors as warnings
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=120 --statistics
	mypy himl/ --ignore-missing-imports

format: ## Format code
	black himl tests

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean ## Build the package
	$(PYTHON) -m build

# Version bumping commands
bump-patch: ## Bump patch version (0.16.4 -> 0.16.5)
	bump-my-version bump patch

bump-minor: ## Bump minor version (0.16.4 -> 0.17.0)
	bump-my-version bump minor

bump-major: ## Bump major version (0.16.4 -> 1.0.0)
	bump-my-version bump major

# Show what version bump would do
show-bump: ## Show what version bumps would result in
	bump-my-version show-bump

# Dry run version bumps
dry-bump-patch: ## Dry run patch version bump
	bump-my-version bump --dry-run --allow-dirty patch

dry-bump-minor: ## Dry run minor version bump
	bump-my-version bump --dry-run --allow-dirty minor

dry-bump-major: ## Dry run major version bump
	bump-my-version bump --dry-run --allow-dirty major

release: build ## Build and upload to PyPI (requires proper credentials)
	$(PYTHON) -m twine upload dist/*
