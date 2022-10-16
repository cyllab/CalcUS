#!/bin/sh
sleep 5

if [[ -z $CALCUS_CLOUD ]];
then
    echo "Cloud mode detected, no celery worker needed"
else
    celery -A calcus worker -Q celery --concurrency=1 -B -s scr/celerybeat-schedule
fi
