#!/bin/sh
sleep 5
celery -A calcus worker -Q celery --concurrency=1 -B
