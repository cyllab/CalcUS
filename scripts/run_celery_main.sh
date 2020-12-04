#!/bin/sh
sleep 5
su -m calcus -c "celery -A calcus -Q celery --concurrency=1 worker -B"  
