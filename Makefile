.PHONY: dev dev-api dev-worker dev-web test test-backend test-unit test-frontend lint lint-fix migrate migrate-create docker-up docker-down docker-build docker-logs sanitize-test check-docs audit security-test clean

# --- Development ---

dev:
	docker compose up -d

dev-api:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-worker:
	cd worker && celery -A celery_app worker --loglevel=info --queues=tpaper

dev-web:
	cd web && npm run dev

# --- Testing ---

test: test-backend test-frontend

test-backend:
	.venv/bin/python -m pytest tests/unit/ -v --tb=short

test-unit:
	.venv/bin/python -m pytest tests/unit/ -v --tb=short

test-frontend:
	cd web && npm run lint

sanitize-test:
	.venv/bin/python scripts/sanitize_test.py --all

security-test:
	.venv/bin/python -m pytest tests/unit/test_security.py tests/unit/test_security_hardening.py tests/unit/test_prompt_injection.py -v --tb=short

# --- Linting ---

lint:
	cd backend && ruff check .
	cd backend && ruff format --check .
	cd web && npm run lint

lint-fix:
	cd backend && ruff check --fix .
	cd backend && ruff format .
	cd web && npm run lint:fix

# --- Documentation ---

check-docs:
	.venv/bin/python scripts/check_docs.py

# --- Security ---

audit:
	@echo "=== Python 依赖漏洞扫描 ==="
	.venv/bin/python -m pip_audit
	@echo ""
	@echo "=== npm 依赖漏洞扫描 ==="
	cd web && npm audit

# --- Database ---

migrate:
	cd backend && alembic upgrade head

migrate-create:
	cd backend && alembic revision --autogenerate -m "$(MSG)"

# --- Docker ---

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-build:
	docker compose build

docker-logs:
	docker compose logs -f

# --- Maintenance ---

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/build backend/*.egg-info worker/build worker/*.egg-info
