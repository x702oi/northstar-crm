#!/usr/bin/env bash
set -e

gunicorn_threads="${GUNICORN_THREADS:-2}"
gunicorn_workers="${GUNICORN_WORKERS:-2}"
gunicorn_timeout="${GUNICORN_TIMEOUT:-120}"

exec /home/frappe/frappe-bench/env/bin/gunicorn \
  --chdir=/home/frappe/frappe-bench/sites \
  --bind=0.0.0.0:8000 \
  --threads="${gunicorn_threads}" \
  --workers="${gunicorn_workers}" \
  --worker-class=gthread \
  --worker-tmp-dir=/dev/shm \
  --timeout="${gunicorn_timeout}" \
  --preload \
  frappe.app:application
