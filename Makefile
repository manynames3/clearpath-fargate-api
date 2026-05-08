SHELL := /bin/bash
CHECKOV ?= .venv/bin/checkov

.PHONY: install test validate validate-terraform validate-security preflight deployment-evidence dev dev-detached seed smoke logs stop clean dev-local seed-local clean-local

install:
	python3 -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -e "app[dev]"

test:
	.venv/bin/python -m pytest app/tests

validate: test validate-terraform validate-security

validate-terraform:
	terraform fmt -check -recursive terraform
	terraform -chdir=terraform/environments/dev init -backend=false
	terraform -chdir=terraform/environments/dev validate

validate-security:
	$(CHECKOV) -d terraform/ --framework terraform --quiet
	$(CHECKOV) -d k8s/ --framework kubernetes --quiet

preflight:
	scripts/preflight.sh

deployment-evidence:
	scripts/collect-deployment-evidence.sh

dev:
	docker compose up --build

dev-detached:
	docker compose up -d --build

seed:
	docker compose exec api python -m src.seed

smoke:
	curl -f http://localhost:8000/health
	curl -f "http://localhost:8000/api/market/gwinnett"
	curl -f "http://localhost:8000/api/leads?county=Gwinnett&limit=5"

logs:
	docker compose logs -f api

stop:
	docker compose down

clean:
	docker compose down -v

dev-local:
	ENVIRONMENT=local DATABASE_URL=sqlite+aiosqlite:///./clearpath-local.db LOCAL_CREATE_TABLES=true PYTHONPATH=app .venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

seed-local:
	ENVIRONMENT=local DATABASE_URL=sqlite+aiosqlite:///./clearpath-local.db LOCAL_CREATE_TABLES=true PYTHONPATH=app .venv/bin/python -m src.seed

clean-local:
	rm -f clearpath-local.db
