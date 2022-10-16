#!/bin/sh
sleep 5

# Fix for OpenMPI in Docker
export OMPI_MCA_btl_vader_single_copy_mechanism=none

if [[ -z $CALCUS_CLOUD ]];
then
    echo "Cloud mode detected, no celery worker needed"
else
    celery -A calcus worker -Q comp --concurrency=1
fi
