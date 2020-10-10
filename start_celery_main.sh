#!/bin/bash

echo "frontend/tasks.py" | entr -r celery -A calcus -Q celery --concurrency=1 worker -B
