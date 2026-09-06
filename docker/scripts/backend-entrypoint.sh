#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec uvicorn pensieve.asgi:application \
  --host 0.0.0.0 \
  --port "${PORT:-8000}"
