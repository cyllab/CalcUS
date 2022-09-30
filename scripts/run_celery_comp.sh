#!/bin/sh
sleep 5
if [ $CALCUS_CLOUD != "" ]
then
    echo "Cloud mode detected, no celery worker needed"
else
    celery -A calcus worker -Q comp --concurrency=1
fi
