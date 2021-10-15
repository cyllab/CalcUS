#!/bin/sh

python scripts/wait_for_postgres.py
python manage.py makemigrations
python manage.py makemigrations frontend
python manage.py migrate
python manage.py init_static_obj
python manage.py check_su

gunicorn calcus.wsgi:application --bind 0.0.0.0:8000 --access-logfile=- --error-logfile=-
