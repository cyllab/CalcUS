#!/bin/bash

mkdir -p data
docker-compose down --remove-orphans
docker image prune -f
git pull
docker-compose -f dev-compose.yml build
docker-compose -f dev-compose.yml -f docker-compose.override.yml up
