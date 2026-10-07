.PHONY: check db-up db-down image image-scan infra-check migrate run

check:
	python scripts/check.py

db-up:
	docker compose up --detach --wait db

db-down:
	docker compose down

image:
	python scripts/container_smoke.py

image-scan:
	python scripts/image_scan.py

infra-check:
	python scripts/infra_check.py

migrate:
	python -m alembic upgrade head

run:
	uvicorn serviceflow.main:app --app-dir src --reload
