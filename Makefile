.PHONY: setup test deploy-dev release-dev smoke demo
PY ?= .venv/bin/python

setup:
	python3 -m venv .venv && .venv/bin/pip install -e '.[dev]' build

test:
	.venv/bin/ruff check .
	@if [ -z "$$PG_TEST_DSN" ]; then echo "PG_TEST_DSN unset: Postgres tests are skipped"; fi
	$(PY) -m pytest -q

deploy-dev:
	databricks bundle deploy -t dev
	$(PY) -m scripts.migrate_lakebase

release-dev:
	databricks bundle run agentops_release_pipeline -t dev

smoke:
	$(PY) -m scripts.smoke_e2e --upto M7 --live

demo:
	@echo "See docs/RUNBOOK.md, section 'Two-minute demo'"
