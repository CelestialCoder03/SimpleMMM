#!/usr/bin/env sh
set -eu

# Run migrations only if RUN_MIGRATIONS is set to "true" (default: true)
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Running database migrations..."
  alembic upgrade head
else
  echo "Skipping database migrations (RUN_MIGRATIONS=${RUN_MIGRATIONS:-not set})"
fi

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

exec gunicorn -k uvicorn.workers.UvicornWorker -w "${WEB_CONCURRENCY:-2}" -b 0.0.0.0:8000 app.main:app
