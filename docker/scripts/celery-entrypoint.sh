#!/bin/sh
set -e
ROLE="${CELERY_ROLE:-worker}"
if [ "$ROLE" = "beat" ]; then
  exec celery -A pensieve beat --loglevel=INFO
fi
exec celery -A pensieve worker --loglevel=INFO
