#!/bin/bash
# Single-service entrypoint: Django (gunicorn) stays private on 127.0.0.1:8000,
# Next.js is the only process bound to Railway's public $PORT and proxies
# /api, /admin, /static to Django internally (see web/next.config.mjs rewrites).
# If either process dies, this script exits so Railway restarts the container.
set -euo pipefail

cd /app/api
python manage.py migrate --noinput
python manage.py collectstatic --noinput
# Browser uploads PUT straight to R2 and need the bucket CORS rule. Non-fatal:
# an R2 token without bucket-admin rights can't set it, and that alone
# shouldn't keep the whole site from booting — the warning says what to fix.
python manage.py configure_r2_cors \
  || echo "WARNING: could not set R2 CORS; browser uploads will fail until it is set (see README)." >&2

# 300s (not the default 120s): a sync worker handling a product media/file
# upload has to fully receive the body *and then* write it on to R2 in the
# same request — on a large video plus anything but a fast connection, 120s
# wasn't enough and gunicorn killed the worker mid-upload, which the browser
# only ever saw as a dropped connection (a generic "please try again", no
# real error). Doesn't affect normal fast requests at all, only gives slow
# ones more room before being killed.
gunicorn config.wsgi:application \
  --bind 127.0.0.1:8000 \
  --workers "${WEB_CONCURRENCY:-3}" \
  --timeout 300 &
DJANGO_PID=$!

cd /app/web
PORT="${PORT:-3000}" HOSTNAME="0.0.0.0" API_INTERNAL_URL="http://127.0.0.1:8000" node server.js &
NEXT_PID=$!

wait -n "$DJANGO_PID" "$NEXT_PID"
exit_code=$?
kill "$DJANGO_PID" "$NEXT_PID" 2>/dev/null || true
exit "$exit_code"
