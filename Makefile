.PHONY: check db-up db-down migrate run

check:
	python scripts/check.py

db-up:
	docker compose up --detach --wait db

db-down:
	docker compose down

migrate:
	python -m alembic upgrade head

run:
	uvicorn serviceflow.main:app --app-dir src --reload
