.PHONY: help install setup start stop restart logs clean test

help:
	@echo "Food Service Data Analysis System"
	@echo "=================================="
	@echo "Available commands:"
	@echo "  make install    - Install Python dependencies"
	@echo "  make setup      - Setup database and initialize tables"
	@echo "  make start      - Start all services with Docker Compose"
	@echo "  make stop       - Stop all services"
	@echo "  make restart    - Restart all services"
	@echo "  make logs       - View logs from all services"
	@echo "  make clean      - Remove containers and volumes"
	@echo "  make test       - Run tests"

install:
	pip install -r requirements.txt

setup:
	cp .env.example .env
	@echo "Please edit .env file with your configuration"
	@echo "Then run: make start"

start:
	docker-compose up -d
	@echo "Services starting..."
	@echo "API Gateway: http://localhost:8000"
	@echo "Machine 1 (Data Ingestion): http://localhost:8001"
	@echo "Machine 2 (Analytics): http://localhost:8002"
	@echo "Machine 3 (Insights): http://localhost:8003"
	@echo "Machine 4 (Dashboard): http://localhost:8004"
	@echo "Machine 5 (Carbon): http://localhost:8005"
	@echo "Machine 6 (Chatbot): http://localhost:8006"

stop:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	rm -rf .pytest_cache

test:
	pytest tests/ -v
