#!/bin/bash
sleep 5

if [[ -z "$CALCUS_CLOUD" ]];
then
    celery -A calcus worker -Q celery --concurrency=1 -B -s scr/celerybeat-schedule
else
    echo "Cloud mode detected, no celery worker needed"
fi
