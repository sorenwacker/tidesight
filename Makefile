.PHONY: up down backend frontend install test docs lint

# Start all services
up:
	@echo "Starting backend and frontend..."
	@make backend &
	@make frontend

# Stop all services
down:
	@pkill -f "uvicorn tidesight.main:app" || true
	@pkill -f "vite" || true
	@echo "Services stopped"

# Start backend only
backend:
	uv run uvicorn tidesight.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend only
frontend:
	cd frontend && npm run dev

# Install all dependencies
install:
	uv sync --all-extras
	cd frontend && npm install

# Run tests
test:
	uv run pytest tests/ -v

# Serve documentation
docs:
	uv run mkdocs serve

# Lint code
lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/
