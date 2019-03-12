#!/bin/bash

# goto workdir
cd /app

# run migrations
python manage.py makemigrations ip16dash
python manage.py migrate

# start service
python manage.py runserver 0.0.0.0:8000