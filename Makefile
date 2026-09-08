.PHONY: dev-up dev-down test lint api worker chaos slo-demo
dev-up:
	docker compose up --build -d
dev-down:
	docker compose down -v
dev-logs:
	docker compose logs -f api worker
api:
	uvicorn app.main:app --reload --port 8000
worker:
	python -m app.worker
test:
	pytest -q
lint:
	ruff check app failure-engine slo-engine remediation-engine tests
chaos:
	python failure-engine/failurectl.py error --rate 0.5
slo-demo:
	python slo-engine/slo.py --log benchmarks/sample-requests.jsonl --target 99.9
