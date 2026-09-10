#!/bin/sh
set -e
ROLE="${CELERY_ROLE:-worker}"
if [ "$ROLE" = "beat" ]; then
  exec celery -A pensieve beat --loglevel=INFO
fi
# solo pool avoids prefork OOM on 1GB EC2 instances (default concurrency forks = CPU count).
POOL="${CELERY_POOL:-solo}"
CONCURRENCY="${CELERY_CONCURRENCY:-1}"
exec celery -A pensieve worker --loglevel=INFO --pool="$POOL" --concurrency="$CONCURRENCY"
