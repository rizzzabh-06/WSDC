.PHONY: install start-github-app start-backend start-worker

install:
	@echo "Installing GitHub App dependencies..."
	cd github-app && npm install
	@echo "Installing Backend dependencies..."
	cd backend && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
	@echo "Installation complete."

start-github-app:
	@echo "Starting GitHub App locally..."
	cd github-app && npm start

start-backend:
	@echo "Starting FastAPI Backend locally..."
	cd backend && ./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload

start-worker:
	@echo "Starting Celery Worker locally..."
	cd backend && ./venv/bin/celery -A worker app worker --loglevel=info

start-all:
	@echo "Starting all services (requires a terminal multiplexer or open 3 separate tabs)..."
	@echo "Run 'make start-github-app' in tab 1"
	@echo "Run 'make start-backend' in tab 2"
	@echo "Run 'make start-worker' in tab 3"
