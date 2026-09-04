.PHONY: install install-dev install-all uninstall clean test lint format help

# Variables
PYTHON := python3
PIP := pip3
PACKAGE_NAME := heybro
PACKAGE_DIR := src/heybro_app
MAIN_SCRIPT := src/heybro.py
VENV := env

# Default target
all: help

# Installation targets
install: ## Install heybro CLI in development mode with core dependencies
	@echo "📦 Installing heybro CLI (core dependencies)..."
	$(PIP) install -e .
	@echo "✅ Installation complete!"
	@echo ""
	@echo "💡 Next steps:"
	@echo "   1. Set up your API keys:"
	@echo "      - OpenAI: export OPENAI_API_KEY='your-key'"
	@echo "      - AWS: export AWS_PROFILE='your-profile' or export AWS_ACCESS_KEY_ID='...'"
	@echo "   2. Run: heybro --help"

install-dev: ## Install with development dependencies
	@echo "📦 Installing heybro CLI (development mode)..."
	$(PIP) install -e ".[dev]"
	@echo "✅ Development installation complete!"

install-all: ## Install with all optional dependencies
	@echo "📦 Installing heybro CLI (all dependencies)..."
	$(PIP) install -e ".[all]"
	@echo "✅ Full installation complete!"

# Uninstallation
uninstall: ## Uninstall heybro CLI
	@echo "🗑️  Uninstalling heybro CLI..."
	-$(PIP) uninstall -y $(PACKAGE_NAME) 2>/dev/null || true
	@echo "✅ Uninstallation complete"

# Cleaning
clean: ## Clean build artifacts and caches
	@echo "🧹 Cleaning build artifacts..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf build/ dist/ .pytest_cache/ .mypy_cache/ 2>/dev/null || true
	@echo "✅ Clean complete"

clean-env: ## Remove virtual environment (USE WITH CAUTION)
	@echo "⚠️  Removing virtual environment..."
	@rm -rf $(VENV)
	@echo "✅ Virtual environment removed"

# Testing
test: ## Run tests
	@echo "🧪 Running tests..."
	$(PYTHON) -m pytest tests/ -v

test-cov: ## Run tests with coverage
	@echo "🧪 Running tests with coverage..."
	$(PYTHON) -m pytest tests/ --cov=$(PACKAGE_DIR) --cov-report=html --cov-report=term

# Code quality
lint: ## Run linting
	@echo "🔍 Running linting..."
	$(PYTHON) -m flake8 $(PACKAGE_DIR) $(MAIN_SCRIPT)
	$(PYTHON) -m pylint $(PACKAGE_DIR) $(MAIN_SCRIPT)

format: ## Format code
	@echo "🎨 Formatting code..."
	$(PYTHON) -m black $(PACKAGE_DIR) $(MAIN_SCRIPT)
	$(PYTHON) -m isort $(PACKAGE_DIR) $(MAIN_SCRIPT)

format-check: ## Check code formatting
	@echo "🔍 Checking code formatting..."
	$(PYTHON) -m black --check $(PACKAGE_DIR) $(MAIN_SCRIPT)
	$(PYTHON) -m isort --check-only $(PACKAGE_DIR) $(MAIN_SCRIPT)

# Distribution
build: clean ## Build distribution packages
	@echo "📦 Building distribution packages..."
	$(PYTHON) -m build
	@echo "✅ Build complete - check dist/ directory"

upload-test: build ## Upload to Test PyPI
	@echo "☁️  Uploading to Test PyPI..."
	$(PYTHON) -m twine upload --repository testpypi dist/*

upload: build ## Upload to PyPI
	@echo "☁️  Uploading to PyPI..."
	$(PYTHON) -m twine upload dist/*

# Setup and configuration
setup: ## Interactive setup for first-time users
	@echo "🚀 Welcome to heybro CLI setup!"
	@echo ""
	@read -p "Do you want to install optional dependencies? (y/n) " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(MAKE) install-all; \
	else \
		$(MAKE) install; \
	fi

# Documentation
docs: ## Build documentation
	@echo "📖 Building documentation..."
	@$(PYTHON) -m pydoc -w $(PACKAGE_DIR)/*.py
	@echo "✅ Documentation generated"

# Running
run: ## Run heybro CLI directly (without installation)
	$(PYTHON) $(MAIN_SCRIPT)

# Docker (optional)
docker-build: ## Build Docker image
	docker build -t heybro:latest .

docker-run: ## Run heybro in Docker
docker run --rm -it \
		-e OPENAI_API_KEY=$$OPENAI_API_KEY \
		-e AWS_PROFILE=$$AWS_PROFILE \
		-v $$HOME/.aws:/root/.aws:ro \
		heybro:latest

# Help
help: ## Show this help message
	@echo "heybro CLI - Makefile"
	@echo "====================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Usage examples:"
	@echo "  make install       # Install with core dependencies"
	@echo "  make install-all   # Install with all features"
	@echo "  make clean         # Clean build artifacts"
	@echo "  make test          # Run tests"
	@echo "  make help          # Show this message"

# Development shortcuts
dev: install-dev lint test ## Full development cycle (install, lint, test)

# System dependencies (macOS)
brew-deps: ## Install system dependencies via Homebrew (macOS only)
	@echo "🍺 Installing system dependencies..."
	@which brew >/dev/null 2>&1 || { echo "Error: Homebrew not found"; exit 1; }
	brew install vim
	@echo "✅ System dependencies installed"

# System dependencies (Ubuntu/Debian)
apt-deps: ## Install system dependencies via apt (Ubuntu/Debian)
	@echo "📦 Installing system dependencies..."
	@which apt >/dev/null 2>&1 || { echo "Error: apt not found"; exit 1; }
	sudo apt update
	sudo apt install -y vim
	@echo "✅ System dependencies installed"

# Check requirements
check: ## Check system requirements
	@echo "🔍 Checking system requirements..."
	@$(PYTHON) --version >/dev/null 2>&1 && echo "✓ Python found" || echo "✗ Python not found"
	@which vim >/dev/null 2>&1 && echo "✓ Vim found" || echo "⚠ Vim not found (optional for /vim command)"
	@echo "✅ System check complete"

# Version
version: ## Show version
	@$(PYTHON) $(MAIN_SCRIPT) --version 2>/dev/null || echo "Version: development"