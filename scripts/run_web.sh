#!/bin/sh
su -m calcus -c "python manage.py makemigrations"
su -m calcus -c "python manage.py makemigrations frontend"
su -m calcus -c "python manage.py migrate"
su -m calcus -c "gunicorn calcus.wsgi:application --bind 0.0.0.0:8000"
