#!/bin/bash

# Building the test image to make sure that it exists and has the freshest code
docker compose -f test-compose.yml build

docker compose -f test-compose.yml -f test-compose.override.yml run web /calcus/scripts/run_coverage_tests.sh
