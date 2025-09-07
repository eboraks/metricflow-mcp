# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Install system dependencies required for psycopg2 and pgvector
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Configure Poetry: install venv inside project + cache location
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV POETRY_CACHE_DIR="/tmp/poetry_cache"

WORKDIR /app

# Copy dependency files first (for Docker cache efficiency)
COPY pyproject.toml poetry.lock* ./

# Install dependencies (without project itself for faster rebuilds)
RUN poetry install --no-root

# Copy the rest of the application code
COPY src ./src
COPY .env .env

# Run the MCP server (entrypoint)
CMD ["poetry", "run", "python", "src/server.py"]
