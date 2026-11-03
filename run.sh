#!/bin/sh
cd /var/task
exec python -m gunicorn --bind 0.0.0.0:8080 --workers 1 --threads 2 --timeout 120 --chdir backend app:app
