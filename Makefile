.PHONY: help install build validate deploy deploy-app deploy-all deploy-dev deploy-prod destroy clean \
        run stop restart refresh-token setup-local lint lint-fix format format-check

# Configuration
TARGET ?= development
PROFILE ?= DEFAULT

help:
	@echo "Tellr - Databricks Asset Bundle Deployment"
	@echo ""
	@echo "Local Development:"
	@echo "  make setup-local   Install Python deps and setup local environment"
	@echo "  make run           Start the app locally"
	@echo "  make stop          Stop the local app"
	@echo "  make restart       Restart the local app"
	@echo "  make refresh-token Refresh Databricks OAuth token in .env"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          Run ruff linter"
	@echo "  make lint-fix      Run ruff linter with auto-fix"
	@echo "  make format        Format code with ruff"
	@echo "  make format-check  Check code formatting"
	@echo ""
	@echo "Bundle Deployment:"
	@echo "  make install       Install frontend dependencies"
	@echo "  make build         Build frontend for production"
	@echo "  make validate      Validate bundle configuration"
	@echo "  make deploy        Build and deploy bundle to TARGET"
	@echo "  make deploy-app    Deploy app source code to Databricks"
	@echo "  make deploy-all    Deploy bundle and app (full deployment)"
	@echo "  make deploy-dev    Full deploy to development"
	@echo "  make deploy-prod   Full deploy to production"
	@echo "  make destroy       Destroy deployment for TARGET"
	@echo "  make clean         Clean build artifacts"
	@echo ""
	@echo "Examples:"
	@echo "  make run                           # Start local dev server"
	@echo "  make refresh-token PROFILE=myprof  # Refresh token using profile"
	@echo "  make deploy TARGET=production"
	@echo "  make lint-fix                      # Fix linting issues"

# ============== Local Development ==============

# Setup local development environment
setup-local:
	@echo "Setting up local development environment..."
	python3 -m venv .venv || true
	. .venv/bin/activate && pip install -e ".[dev]"
	cd frontend && npm install
	@echo "Done. Run 'source .venv/bin/activate' to activate the virtual environment."

# Start local app
run:
	./start_app.sh

# Stop local app
stop:
	./stop_app.sh

# Restart local app (stop + start)
restart:
	./stop_app.sh
	./start_app.sh

# Refresh Databricks OAuth token and update .env
refresh-token:
	@echo "Refreshing Databricks token using profile: $(PROFILE)"
	@TOKEN=$$(databricks auth token --profile $(PROFILE) 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])"); \
	if [ -z "$$TOKEN" ]; then \
		echo "Failed to get token. Run 'databricks auth login --profile $(PROFILE)' first."; \
		exit 1; \
	fi; \
	if grep -q "^DATABRICKS_TOKEN=" .env 2>/dev/null; then \
		sed -i '' "s|^DATABRICKS_TOKEN=.*|DATABRICKS_TOKEN=$$TOKEN|" .env; \
	else \
		echo "DATABRICKS_TOKEN=$$TOKEN" >> .env; \
	fi; \
	echo "Token refreshed successfully."

# ============== Code Quality ==============

# Run ruff linter
lint:
	uvx ruff check src/ tests/

# Run ruff linter with auto-fix
lint-fix:
	uvx ruff check --fix src/ tests/

# Format code with ruff
format:
	uvx ruff format src/ tests/

# Check code formatting
format-check:
	uvx ruff format --check src/ tests/

# ============== Bundle Deployment ==============

# Install frontend dependencies
install:
	cd frontend && npm install

# Build frontend
build: install
	cd frontend && npm run build

# Validate bundle
validate:
	databricks bundle validate --target $(TARGET) --profile $(PROFILE)

# Deploy bundle (builds frontend first)
deploy: build validate
	databricks bundle deploy --target $(TARGET) --profile $(PROFILE)

# Deploy app source code
deploy-app:
	@echo "Deploying app to Databricks..."
	databricks apps deploy tellr-$(TARGET) \
		--source-code-path "$$(databricks bundle summary --target $(TARGET) --profile $(PROFILE) 2>/dev/null | grep 'Path:' | awk '{print $$2}')/files" \
		--profile $(PROFILE)

# Full deployment: bundle + app
deploy-all: deploy deploy-app
	@echo "Full deployment complete!"

# Convenience targets
deploy-dev:
	$(MAKE) deploy-all TARGET=development PROFILE=$(PROFILE)

deploy-prod:
	$(MAKE) deploy-all TARGET=production PROFILE=$(PROFILE)

# Destroy deployment
destroy:
	databricks bundle destroy --target $(TARGET) --profile $(PROFILE)

# Clean build artifacts
clean:
	rm -rf frontend/dist
	rm -rf frontend/node_modules
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
