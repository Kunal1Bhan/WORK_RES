.PHONY: dev-up dev-down test lint api worker chaos slo-demo kind-up kind-down k8s-deploy k8s-chaos bench gui
gui:
	python lab_gui.py
dev-up:
	docker compose up --build -d
dev-down:
	docker compose down -v
dev-logs:
	docker compose logs -f api worker
kind-up:
	kind create cluster --name lab --wait 300s
kind-down:
	kind delete cluster --name lab
k8s-deploy:
	kubectl apply -f deploy/kubernetes/ && kubectl rollout status deployment/lab-api --timeout=180s
k8s-chaos:
	python failure-engine/k8s.py kill-pods --selector app=lab-api
api:
	uvicorn app.main:app --reload --port 8000
worker:
	python -m app.worker
test:
	pytest -q
lint:
	ruff check app failure-engine slo-engine remediation-engine traffic-engine dr-engine gpu-scheduler model-serving benchmarks tests
chaos:
	python failure-engine/failurectl.py error --rate 0.5
bench:
	python benchmarks/loadtest.py --base http://127.0.0.1:8000 --rps 60 --seconds 20
slo-demo:
	python slo-engine/slo.py --log benchmarks/sample-requests.jsonl --target 99.9
