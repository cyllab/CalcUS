#!/bin/sh
sleep 5
su -m calcus -c "celery -A calcus -Q comp --concurrency=1 worker"  
