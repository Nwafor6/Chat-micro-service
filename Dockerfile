FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install poetry

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Configure poetry to not create a virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-root

# Copy project
COPY . .

# Set default environment variables (can be overridden by docker-compose or runtime)
ENV APP_NAME="Global Chat Service"
ENV APP_DESCRIPTION="Real-time chat microservice with JWT authentication"
ENV APP_VERSION="1.0.0"
ENV API_PREFIX="/api/v1"
ENV ENV="development"
ENV DEBUG="true"
ENV DB_TYPE="postgres"
ENV JWT_ALGORITHM="HS256"
ENV JWT_TOKEN_TTL="10080"
ENV REDIS_DB="0"
ENV REDIS_PASSWORD=""
ENV WS_HEARTBEAT_INTERVAL="30"
ENV WS_CONNECTION_TIMEOUT="300"
ENV MAX_CONNECTIONS_PER_USER="5"
ENV MAX_MESSAGE_LENGTH="2000"
ENV MESSAGE_HISTORY_LIMIT="100"
ENV CHAT_ROOM_MEMBER_LIMIT="100"
ENV FILE_UPLOAD_MAX_SIZE="10485760"
ENV LOG_LEVEL="INFO"
ENV LOG_FORMAT="json"

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run uvicorn for FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]