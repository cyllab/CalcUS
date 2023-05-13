#!/bin/sh

python scripts/wait_for_postgres.py
./scripts/migrate.sh
python manage.py check_su

gunicorn calcus.wsgi:application --bind 0.0.0.0:8000 --access-logfile=- --error-logfile=- --reload --timeout $GUNICORN_TIMEOUT --keep-alive $GUNICORN_TIMEOUT
