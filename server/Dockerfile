FROM python:3.12-slim AS base

# Install system dependencies for pygit2, IfcOpenShell, and Node.js
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libgit2-dev \
    build-essential \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Node.js dependencies for fragment conversion
COPY server/package.json server/package-lock.json* ./
RUN npm install --production 2>/dev/null || true

# Copy application code
COPY server/ .

# Create data directories
RUN mkdir -p /data/repos /data/cache /data/working

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
