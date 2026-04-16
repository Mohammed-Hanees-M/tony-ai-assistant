.PHONY: run test clean shell

run:
	uvicorn apps.backend.main:app --reload

test:
	pytest tests/unit tests/integration -q

verify:
	python scripts/verify_cognitive_controller.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

shell:
	python
