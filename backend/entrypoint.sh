#!/bin/sh
set -o errexit
set -o pipefail

until python manage.py migrate --noinput; do
  echo "Waiting for database connection..."
  sleep 3
done

python -c "
import pathlib
for d in ['/app/media/mailer', '/app/media/static', '/app/staticfiles']:
    try:
        pathlib.Path(d).mkdir(parents=True, exist_ok=True)
    except PermissionError:
        pass
"

chown -R appuser:appgroup /app/staticfiles /app/media 2>/dev/null || true

if [ "$USE_S3" != "true" ]; then
  python manage.py collectstatic --noinput --skip-checks || true
fi

if [ "$DJANGO_DEBUG" = "true" ]; then
  exec python manage.py runserver 0.0.0.0:8000 --noreload
else
  exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers ${GUNICORN_WORKERS:-3} \
    --threads ${GUNICORN_THREADS:-4} \
    --timeout ${GUNICORN_TIMEOUT:-120} \
    --access-logfile - \
    --error-logfile - \
    --log-level ${GUNICORN_LOG_LEVEL:-info}
fi
