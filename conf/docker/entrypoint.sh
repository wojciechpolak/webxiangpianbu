#!/bin/bash

export DJANGO_SETTINGS_MODULE=run.settings_docker

python manage.py collectstatic --no-input
chgrp -R users /app/static/ && chmod -R g+w /app/static

/usr/local/bin/supervisord -c /etc/supervisord.conf
