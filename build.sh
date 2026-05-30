#!/bin/bash
set -o errexit

pip install -r requirements.txt
mkdir -p static staticfiles
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py create_superuser
