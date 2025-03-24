#!/bin/bash

echo "⏳ Waiting for database to be ready..."
sleep 5

alembic upgrade head

gunicorn src.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind=0.0.0.0:8000
