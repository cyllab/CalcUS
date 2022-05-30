#!/bin/bash

mkdir -p data

docker-compose down --remove-orphans
docker-compose -f test-compose.yml -f test-compose.override.yml build
docker-compose -f test-compose.yml -f test-compose.override.yml up
