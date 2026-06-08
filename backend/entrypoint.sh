#!/bin/sh
set -o errexit
set -o pipefail

until python manage.py migrate --noinput; do
  echo "Waiting for database connection..."
  sleep 3
done

python manage.py collectstatic --noinput || true

if [ "$DJANGO_DEBUG" = "true" ]; then
  exec python manage.py runserver 0.0.0.0:8000
else
  exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers ${GUNICORN_WORKERS:-4} \
    --timeout ${GUNICORN_TIMEOUT:-120} \
    --access-logfile - \
    --error-logfile - \
    --log-level ${GUNICORN_LOG_LEVEL:-info}
fi
