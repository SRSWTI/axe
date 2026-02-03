.DEFAULT_GOAL := prepare

.PHONY: help
help: ## Show available make targets.
	@echo "Available make targets:"
	@awk 'BEGIN { FS = ":.*## " } /^[A-Za-z0-9_.-]+:.*## / { printf "  %-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

.PHONY: install-prek
install-prek: ## Install prek and repo git hooks.
	@echo "==> Installing prek"
	@uv tool install prek
	@echo "==> Installing git hooks with prek"
	@uv tool run prek install

.PHONY: prepare
prepare: download-deps install-prek ## Sync dependencies for all workspace packages and install prek hooks.
	@echo "==> Syncing dependencies for all workspace packages"
	@uv sync --frozen --all-extras --all-packages

.PHONY: prepare-build
prepare-build: download-deps ## Sync dependencies for releases without workspace sources.
	@echo "==> Syncing dependencies for release builds (no sources)"
	@uv sync --all-extras --all-packages --no-sources

.PHONY: format format-axe-cli format-kosong format-pykaos format-axe-sdk
format: format-axe-cli format-kosong format-pykaos format-axe-sdk ## Auto-format all workspace packages with ruff.
format-axe-cli: ## Auto-format Axe Code CLI sources with ruff.
	@echo "==> Formatting Axe Code CLI sources"
	@uv run ruff check --fix
	@uv run ruff format
format-kosong: ## Auto-format kosong sources with ruff.
	@echo "==> Formatting kosong sources"
	@uv run --project packages/kosong --directory packages/kosong ruff check --fix
	@uv run --project packages/kosong --directory packages/kosong ruff format
format-pykaos: ## Auto-format pykaos sources with ruff.
	@echo "==> Formatting pykaos sources"
	@uv run --project packages/kaos --directory packages/kaos ruff check --fix
	@uv run --project packages/kaos --directory packages/kaos ruff format
format-axe-sdk: ## Auto-format axe-sdk sources with ruff.
	@echo "==> Formatting axe-sdk sources"
	@uv run --project sdks/axe-sdk --directory sdks/axe-sdk ruff check --fix
	@uv run --project sdks/axe-sdk --directory sdks/axe-sdk ruff format

.PHONY: check check-axe-cli check-kosong check-pykaos check-axe-sdk
check: check-axe-cli check-kosong check-pykaos check-axe-sdk ## Run linting and type checks for all packages.
check-axe-cli: ## Run linting and type checks for Axe Code CLI.
	@echo "==> Checking Axe Code CLI (ruff + pyright + ty; ty is non-blocking)"
	@uv run ruff check
	@uv run ruff format --check
	@uv run pyright
	@uv run ty check || true
check-kosong: ## Run linting and type checks for kosong.
	@echo "==> Checking kosong (ruff + pyright + ty; ty is non-blocking)"
	@uv run --project packages/kosong --directory packages/kosong ruff check
	@uv run --project packages/kosong --directory packages/kosong ruff format --check
	@uv run --project packages/kosong --directory packages/kosong pyright
	@uv run --project packages/kosong --directory packages/kosong ty check || true
check-pykaos: ## Run linting and type checks for pykaos.
	@echo "==> Checking pykaos (ruff + pyright + ty; ty is non-blocking)"
	@uv run --project packages/kaos --directory packages/kaos ruff check
	@uv run --project packages/kaos --directory packages/kaos ruff format --check
	@uv run --project packages/kaos --directory packages/kaos pyright
	@uv run --project packages/kaos --directory packages/kaos ty check || true
check-axe-sdk: ## Run linting and type checks for axe-sdk.
	@echo "==> Checking axe-sdk (ruff + pyright + ty; ty is non-blocking)"
	@uv run --project sdks/axe-sdk --directory sdks/axe-sdk ruff check
	@uv run --project sdks/axe-sdk --directory sdks/axe-sdk ruff format --check
	@uv run --project sdks/axe-sdk --directory sdks/axe-sdk pyright
	@uv run --project sdks/axe-sdk --directory sdks/axe-sdk ty check || true


.PHONY: test test-axe-cli test-kosong test-pykaos test-axe-sdk
test: test-axe-cli test-kosong test-pykaos test-axe-sdk ## Run all test suites.
test-axe-cli: ## Run Axe Code CLI tests.
	@echo "==> Running Axe Code CLI tests"
	@uv run pytest tests -vv
	@uv run pytest tests_e2e -vv
test-kosong: ## Run kosong tests (including doctests).
	@echo "==> Running kosong tests"
	@uv run --project packages/kosong --directory packages/kosong pytest --doctest-modules -vv
test-pykaos: ## Run pykaos tests.
	@echo "==> Running pykaos tests"
	@uv run --project packages/kaos --directory packages/kaos pytest tests -vv
test-axe-sdk: ## Run axe-sdk tests.
	@echo "==> Running axe-sdk tests"
	@uv run --project sdks/axe-sdk --directory sdks/axe-sdk pytest tests -vv

.PHONY: build build-axe-cli build-kosong build-pykaos build-axe-sdk build-bin build-bin-onedir
build: build-axe-cli build-kosong build-pykaos build-axe-sdk ## Build Python packages for release.
build-axe-cli: ## Build the axe CLI sdist and wheel.
	@echo "==> Building axe distributions"
	@uv build --no-sources --out-dir dist
build-kosong: ## Build the kosong sdist and wheel.
	@echo "==> Building kosong distributions"
	@uv build --package kosong --no-sources --out-dir dist/kosong
build-pykaos: ## Build the pykaos sdist and wheel.
	@echo "==> Building pykaos distributions"
	@uv build --package pykaos --no-sources --out-dir dist/pykaos
build-axe-sdk: ## Build the axe-sdk sdist and wheel.
	@echo "==> Building axe-sdk distributions"
	@uv build --package axe-sdk --no-sources --out-dir dist/axe-sdk
build-bin: ## Build the standalone executable with PyInstaller (one-file mode).
	@echo "==> Building PyInstaller binary (one-file)"
	@uv run pyinstaller axe.spec
	@mkdir -p dist/onefile
	@if [ -f dist/axe.exe ]; then mv dist/axe.exe dist/onefile/; elif [ -f dist/axe ]; then mv dist/axe dist/onefile/; fi
build-bin-onedir: ## Build the standalone executable with PyInstaller (one-dir mode).
	@echo "==> Building PyInstaller binary (one-dir)"
	@rm -rf dist/onedir dist/axe
	@uv run pyinstaller axe.spec
	@if [ -f dist/axe/axe-exe.exe ]; then mv dist/axe/axe-exe.exe dist/axe/axe.exe; elif [ -f dist/axe/axe-exe ]; then mv dist/axe/axe-exe dist/axe/axe; fi
	@mkdir -p dist/onedir && mv dist/axe dist/onedir/

.PHONY: ai-test
ai-test: ## Run the test suite with Axe Code CLI.
	@echo "==> Running AI test suite"
	@uv run tests_ai/scripts/run.py tests_ai

.PHONY: gen-changelog gen-docs
gen-changelog: ## Generate changelog with Axe Code CLI.
	@echo "==> Generating changelog"
	@uv run axe --yolo --prompt /skill:gen-changelog
gen-docs: ## Generate user docs with Axe Code CLI.
	@echo "==> Generating user docs"
	@uv run axe --yolo --prompt /skill:gen-docs

include src/axe_cli/deps/Makefile
