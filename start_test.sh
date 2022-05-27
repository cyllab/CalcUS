#!/bin/bash

mkdir -p data

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

docker-compose down --remove-orphans
docker-compose -f test-compose.yml -f test-compose.override.yml build
docker-compose -f test-compose.yml -f test-compose.override.yml up
