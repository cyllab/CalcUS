#!/bin/bash

mkdir -p data

docker compose down
docker compose pull
docker image prune -f
docker compose up --remove-orphans
