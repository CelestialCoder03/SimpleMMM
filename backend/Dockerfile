# Backend API Dockerfile
# Uses shared base for dependency installation.
# For restricted networks, build the base first with mirror args:
#   docker build -f Dockerfile.base --build-arg PIP_MIRROR=... --build-arg APT_MIRROR=... -t mmm-base .
#   Then set the FROM below to mmm-base.
FROM python:3.12-slim-bookworm AS base

ARG PIP_MIRROR=""
ARG APT_MIRROR=""

WORKDIR /app

# Install system dependencies (optionally use mirrors)
RUN set -eux; \
    if [ -n "$APT_MIRROR" ]; then \
      if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i \
          -e "s|http://deb.debian.org/debian|${APT_MIRROR}/debian|g" \
          -e "s|http://deb.debian.org/debian-security|${APT_MIRROR}/debian-security|g" \
          /etc/apt/sources.list.d/debian.sources; \
      fi; \
    fi; \
    apt-get -o Acquire::Retries=5 update; \
    apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
      ca-certificates \
      build-essential \
      curl; \
    rm -rf /var/lib/apt/lists/*

# Install uv
RUN if [ -n "$PIP_MIRROR" ]; then \
      pip install --no-cache-dir -i "$PIP_MIRROR" --trusted-host "$(echo $PIP_MIRROR | sed 's|https\?://||;s|/.*||')" uv; \
    else \
      pip install --no-cache-dir uv; \
    fi

# Copy dependency files
COPY pyproject.toml uv.lock README.md ./
COPY app ./app

# Install dependencies
RUN if [ -n "$PIP_MIRROR" ]; then \
      UV_DEFAULT_INDEX="$PIP_MIRROR" UV_INDEX_URL="$PIP_MIRROR" uv sync --frozen --no-dev; \
    else \
      uv sync --frozen --no-dev; \
    fi

ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY . .

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose port
EXPOSE 8000

# Run the application
ENTRYPOINT ["/entrypoint.sh"]
CMD ["sh", "-c", "exec gunicorn -k uvicorn.workers.UvicornWorker -w ${WEB_CONCURRENCY:-2} -b 0.0.0.0:8000 app.main:app"]
