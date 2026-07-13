#!/bin/bash
# Single-service entrypoint: Django (gunicorn) stays private on 127.0.0.1:8000,
# Next.js is the only process bound to Railway's public $PORT and proxies
# /api, /admin, /static to Django internally (see web/next.config.mjs rewrites).
# If either process dies, this script exits so Railway restarts the container.
set -euo pipefail

cd /app/api
python manage.py migrate --noinput
python manage.py collectstatic --noinput

gunicorn config.wsgi:application \
  --bind 127.0.0.1:8000 \
  --workers "${WEB_CONCURRENCY:-3}" \
  --timeout 120 &
DJANGO_PID=$!

cd /app/web
PORT="${PORT:-3000}" HOSTNAME="0.0.0.0" API_INTERNAL_URL="http://127.0.0.1:8000" node server.js &
NEXT_PID=$!

wait -n "$DJANGO_PID" "$NEXT_PID"
exit_code=$?
kill "$DJANGO_PID" "$NEXT_PID" 2>/dev/null || true
exit "$exit_code"
