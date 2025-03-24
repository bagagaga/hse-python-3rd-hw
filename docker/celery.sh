#!/bin/bash

cd /fastapi_app

rm celerybeat-schedule.db

if [[ "$1" == "celery" ]]; then
  celery -A src.tasks.tasks:celery worker --beat --loglevel=info
elif [[ "$1" == "flower" ]]; then
  celery -A src.tasks.tasks:celery flower --broker=redis://redis:6379/0 --port=5555
fi