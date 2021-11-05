#!/bin/bash

docker-compose pull
docker image prune -f
docker-compose up --remove-orphans
