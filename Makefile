.PHONY: help setup test run run-backend run-frontend run-dev docker-up docker-down clean inspect-db

help:
	@echo "Customer Voice AI — Build and Run Targets:"
	@echo "  make setup         - Initialize environment and copy .env"
	@echo "  make test          - Run backend test suite"
	@echo "  make run           - Start FastAPI backend locally (serves both API & Frontend on :8000)"
	@echo "  make run-backend   - Start FastAPI backend locally on :8000"
	@echo "  make run-frontend  - Start React/Vite frontend locally on :5173"
	@echo "  make inspect-db    - View all database tables, row counts, and schema"
	@echo "  make docker-up     - Start Postgres, Kafka, Backend, Frontend via Docker Compose"
	@echo "  make docker-down   - Stop all Docker containers"
	@echo "  make clean         - Remove pycache, temporary caches and test artifacts"

setup:
	./scripts/setup.sh

test:
	PYTHONPATH=backend pytest backend/tests -v

run: run-backend

run-backend:
	./scripts/run_dev.sh

run-frontend:
	cd frontend && npm run dev

inspect-db:
	python3 scripts/inspect_db.py

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
