#!/usr/bin/env sh
set -eu

cd /app/backend

python - <<'PY'
import os
import time
import psycopg

host = os.getenv("DB_HOST", "127.0.0.1")
port = os.getenv("DB_PORT", "5432")
dbname = os.getenv("DB_NAME", "xfcj")
user = os.getenv("DB_USER", "xfcj")
password = os.getenv("DB_PASSWORD", "")

for attempt in range(1, 61):
    try:
        with psycopg.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=3,
        ):
            print("PostgreSQL is ready.")
            break
    except Exception as exc:
        if attempt == 60:
            raise SystemExit(f"PostgreSQL not ready after {attempt} attempts: {exc}") from exc
        time.sleep(1)
PY

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn lottery_backend.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-1}" \
  --threads "${GUNICORN_THREADS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-60}" \
  --max-requests "${GUNICORN_MAX_REQUESTS:-1000}" \
  --max-requests-jitter "${GUNICORN_MAX_REQUESTS_JITTER:-100}" \
  --access-logfile '-' \
  --error-logfile '-'
