FROM python:3.13-slim

# Build arguments
ARG SOURCE_HASH=unknown

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  ENVIRONMENT=production \
  SOURCE_HASH=${SOURCE_HASH}

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  curl \
  gcc \
  libpq-dev \
  nodejs \
  npm \
  && rm -rf /var/lib/apt/lists/* \
  && useradd -m appuser

# Copy only requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
  pip install --no-cache-dir -r requirements.txt

# Copy application code - this layer will change when code changes
# The SOURCE_HASH arg ensures this layer is rebuilt when code changes
COPY --chown=appuser:appuser . .

# Add SOURCE_HASH as a label to track builds
LABEL source_hash=${SOURCE_HASH}

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
