.PHONY: install test demo export validate docker-up docker-down

install:
	pip install -r requirements.txt

test:
	pytest tests/unit -v

demo:
	python scripts/generate_demo_data_report.py

export:
	python scripts/export_google_sheets.py --dry-run

validate:
	python scripts/validate_output.py

docker-up:
	docker compose up -d

docker-down:
	docker compose down
