#!/bin/bash

export DJANGO_SETTINGS_MODULE=run.settings_docker

python manage.py collectstatic --no-input

/usr/local/bin/supervisord -c /etc/supervisord.conf
