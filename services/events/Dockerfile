# FastAPI event ingestion service Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency installation
RUN pip install --no-cache-dir uv

# Copy dependency specification first for layer caching
COPY pyproject.toml ./

# Install dependencies
RUN uv pip install --system -e .

# Copy application source
COPY . .

EXPOSE 8000

# Use uvicorn with 4 workers for production-like local dev
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
