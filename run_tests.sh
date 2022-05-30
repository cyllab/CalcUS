#!/bin/bash

docker-compose -f test-compose.yml -f test-compose.override.yml run web scripts/run_coverage_tests.sh
