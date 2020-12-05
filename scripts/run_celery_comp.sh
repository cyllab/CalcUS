#!/bin/sh
sleep 5
celery -A calcus -Q comp --concurrency=1 worker
