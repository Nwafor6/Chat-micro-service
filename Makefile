.PHONY: make_migration

install:
	poetry install

serve:
	poetry run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

test:
	poetry run pytest

test-coverage:
	poetry run pytest --cov=app --cov-report=term-missing --cov-fail-under=90

migration:
	alembic revision --autogenerate -m "$(m)"

migrate:
	alembic upgrade head

migrate_rollback:
	alembic downgrade -1

migrate_history:
	alembic history

.PHONY: build up down logs shell test

# Build the Docker image
build:
    docker compose -f docker-compose.dev.yml build

# Start the development environment
up:
    docker compose -f docker-compose.dev.yml up -d

# Stop the development environment
down:
    docker compose -f docker-compose.dev.yml down

# View logs
logs:
    docker compose -f docker-compose.dev.yml logs -f

# Get a shell in the web container
shell:
    docker compose -f docker-compose.dev.yml exec web bash

# Run tests
test:
    docker compose -f docker-compose.dev.yml exec web python -m pytest

# Reset database
reset-db:
    docker compose -f docker-compose.dev.yml down -v
    docker compose -f docker-compose.dev.yml up -d postgres_dev
    sleep 10
    docker compose -f docker-compose.dev.yml up -d

# View container status
status:
    docker compose -f docker-compose.dev.yml ps