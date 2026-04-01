.PHONY: help install validate demo ui baseline docker-build docker-run clean

# Default target
help:
	@echo "Incident Response OpenEnv - Development Tasks"
	@echo ""
	@echo "Setup & Validation:"
	@echo "  make install      - Install dependencies"
	@echo "  make validate     - Validate environment setup"
	@echo ""
	@echo "Running:"
	@echo "  make demo         - Run simple demo with rule-based agent"
	@echo "  make ui           - Launch interactive Gradio UI"
	@echo "  make baseline     - Run OpenAI baseline agent (requires API key)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run   - Run Docker container with UI"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean        - Remove generated files"
	@echo ""

install:
	pip install -r requirements.txt

validate:
	python validate.py

demo:
	python example_demo.py

ui:
	python app.py

baseline:
	@if [ -z "$$OPENAI_API_KEY" ]; then \
		echo "ERROR: OPENAI_API_KEY not set"; \
		echo "Run: export OPENAI_API_KEY='sk-...'"; \
		exit 1; \
	fi
	python baseline/run_baseline.py

docker-build:
	docker build -t incident-response-env .

docker-run:
	docker run -p 7860:7860 \
		-e OPENAI_API_KEY="$${OPENAI_API_KEY}" \
		incident-response-env

docker-baseline:
	docker run --rm \
		-e OPENAI_API_KEY="$${OPENAI_API_KEY}" \
		-v $$(pwd)/results:/app/results \
		incident-response-env \
		python baseline/run_baseline.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -f baseline_results.json
	rm -rf .pytest_cache/
	rm -rf dist/ build/ *.egg-info/
