.PHONY: check run

check:
	python scripts/check.py

run:
	uvicorn serviceflow.main:app --app-dir src --reload
