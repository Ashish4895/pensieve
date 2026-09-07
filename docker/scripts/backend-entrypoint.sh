#!/bin/sh
set -eu

python manage.py setup_application
python manage.py collectstatic --noinput

exec uvicorn pensieve.asgi:application \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --forwarded-allow-ips='*'
