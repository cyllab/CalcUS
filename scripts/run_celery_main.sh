#!/bin/sh
sleep 5
celery -A calcus -Q celery --concurrency=1 worker -B
