#!/bin/bash

echo "frontend/tasks.py" | entr -r celery -A calcus -Q comp --concurrency=1 worker
