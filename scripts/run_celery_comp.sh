#!/bin/bash
sleep 5

# Fix for OpenMPI in Docker
export OMPI_MCA_btl_vader_single_copy_mechanism=none

if [[ -z "$CALCUS_CLOUD" ]];
then
    celery -A calcus worker -Q comp --concurrency=1
else
    echo "Cloud mode detected, no celery worker needed"
fi
