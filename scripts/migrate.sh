#!/bin/sh

python manage.py makemigrations
python manage.py makemigrations frontend
python manage.py migrate
python manage.py init_static_obj
