#!/bin/sh
sleep 5
celery -A calcus worker -Q comp --concurrency=1
