#!/bin/bash
docker-compose down --remove-orphans
docker container prune
docker volume prune
docker image prune -a
